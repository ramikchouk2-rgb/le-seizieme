import math
from datetime import datetime
from typing import Any

from app.core.database import get_pool
from app.services.selection_engine import generate_staff_recommendations, haversine_km

MAX_PICKUP_DISTANCE_KM = 20


async def load_vehicles_for_servers(server_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, owner_server_id, vehicle_type, brand, model,
                   seats_total, can_transport_coworkers, is_active
            FROM vehicles
            WHERE owner_server_id = ANY($1::uuid[])
              AND is_active = TRUE
              AND can_transport_coworkers = TRUE
            """,
            server_ids,
        )
        vehicles: dict[str, dict[str, Any]] = {}
        for r in rows:
            vehicles[str(r["owner_server_id"])] = dict(r)
        return vehicles


async def load_vehicle_availability(vehicle_id: str, event_start: datetime, event_end: datetime) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT available
            FROM vehicle_availability
            WHERE vehicle_id = $1
              AND start_datetime <= $2
              AND end_datetime >= $3
            ORDER BY start_datetime DESC
            LIMIT 1
            """,
            vehicle_id,
            event_start,
            event_end,
        )
        if not row:
            return True
        return row["available"]


async def load_server_locations(server_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT server_id, latitude, longitude, area
            FROM server_locations
            WHERE server_id = ANY($1::uuid[])
              AND is_current = TRUE
              AND is_verified = TRUE
            """,
            server_ids,
        )
        locations: dict[str, dict[str, Any]] = {}
        for r in rows:
            locations[str(r["server_id"])] = dict(r)
        return locations


async def recommend_transport(event_id: str) -> dict[str, Any]:
    recommendation = await generate_staff_recommendations(event_id)
    if recommendation.get("status") == "ERROR":
        return {"error": recommendation.get("error", "Event not found"), "transport_status": "ERROR"}

    requirements = recommendation.get("requirements", [])
    selected_servers: list[dict[str, Any]] = []
    seen_server_ids: set[str] = set()

    for req in requirements:
        for sel in req.get("selected", []):
            sid = sel["server_id"]
            if sid not in seen_server_ids:
                seen_server_ids.add(sid)
                selected_servers.append(sel)

    if not selected_servers:
        return {
            "event_id": event_id,
            "transport_status": "NO_SELECTED_STAFF",
            "drivers": [],
            "passengers": [],
            "unassigned_passengers": [],
            "total_selected": 0,
            "total_assigned": 0,
            "total_unassigned": 0,
        }

    event = recommendation["event"]
    event_start = datetime.fromisoformat(event["start_datetime"])
    event_end = datetime.fromisoformat(event["end_datetime"])

    server_ids = [s["server_id"] for s in selected_servers]
    vehicles = await load_vehicles_for_servers(server_ids)
    locations = await load_server_locations(server_ids)

    eligible_drivers: list[dict[str, Any]] = []
    for server in selected_servers:
        sid = server["server_id"]
        vehicle = vehicles.get(sid)
        if not vehicle:
            continue
        if not await load_vehicle_availability(vehicle["id"], event_start, event_end):
            continue
        eligible_drivers.append({
            "server_id": sid,
            "name": server["name"],
            "vehicle_id": vehicle["id"],
            "vehicle_type": vehicle["vehicle_type"],
            "brand": vehicle["brand"],
            "model": vehicle["model"],
            "seats_total": vehicle["seats_total"],
            "available_seats": vehicle["seats_total"] - 1,
            "can_transport_coworkers": vehicle["can_transport_coworkers"],
            "latitude": locations.get(sid, {}).get("latitude"),
            "longitude": locations.get(sid, {}).get("longitude"),
        })

    passengers_pool: list[dict[str, Any]] = []
    assigned_passenger_ids: set[str] = set()
    for server in selected_servers:
        sid = server["server_id"]
        if any(d["server_id"] == sid for d in eligible_drivers):
            continue
        location = locations.get(sid)
        if not location:
            continue
        passengers_pool.append({
            "server_id": sid,
            "name": server["name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        })

    transport_groups: list[dict[str, Any]] = []
    for driver in eligible_drivers:
        driver_lat = driver.get("latitude")
        driver_lon = driver.get("longitude")
        if driver_lat is None or driver_lon is None:
            continue

        eligible_passengers: list[dict[str, Any]] = []
        for passenger in passengers_pool:
            if passenger["server_id"] in assigned_passenger_ids:
                continue
            distance = haversine_km(
                float(driver_lat),
                float(driver_lon),
                float(passenger["latitude"]),
                float(passenger["longitude"]),
            )
            if distance <= MAX_PICKUP_DISTANCE_KM:
                eligible_passengers.append({**passenger, "distance_km": distance})

        eligible_passengers.sort(key=lambda x: x["distance_km"])
        capacity = driver["available_seats"]
        selected_passengers = eligible_passengers[:capacity]

        group_passengers: list[dict[str, Any]] = []
        for idx, p in enumerate(selected_passengers, start=1):
            assigned_passenger_ids.add(p["server_id"])
            group_passengers.append({
                "server_id": p["server_id"],
                "name": p["name"],
                "pickup_order": idx,
                "distance_from_driver_km": p["distance_km"],
            })

        transport_groups.append({
            "driver": {
                "server_id": driver["server_id"],
                "name": driver["name"],
                "vehicle": f"{driver['brand']} {driver['model']}",
                "capacity": driver["seats_total"],
                "available_seats": driver["available_seats"],
                "can_transport_coworkers": driver["can_transport_coworkers"],
            },
            "passengers": group_passengers,
            "estimated_passenger_count": len(group_passengers),
            "estimated_distance_km": round(sum(p["distance_from_driver_km"] for p in group_passengers), 1),
        })

    unassigned_passengers: list[dict[str, Any]] = []
    for passenger in passengers_pool:
        if passenger["server_id"] not in assigned_passenger_ids:
            distance_to_any_driver = None
            for driver in eligible_drivers:
                if driver.get("latitude") is None or driver.get("longitude") is None:
                    continue
                d = haversine_km(
                    float(driver["latitude"]),
                    float(driver["longitude"]),
                    float(passenger["latitude"]),
                    float(passenger["longitude"]),
                )
                if distance_to_any_driver is None or d < distance_to_any_driver:
                    distance_to_any_driver = d

            reason = "No driver available"
            if eligible_drivers:
                if distance_to_any_driver is not None and distance_to_any_driver > MAX_PICKUP_DISTANCE_KM:
                    reason = f"Outside pickup radius ({round(distance_to_any_driver, 1)} km > {MAX_PICKUP_DISTANCE_KM} km)"
                else:
                    reason = "Vehicle capacity reached"

            unassigned_passengers.append({
                "server_id": passenger["server_id"],
                "name": passenger["name"],
                "reason": reason,
            })

    total_assigned = sum(len(g["passengers"]) for g in transport_groups)

    return {
        "event_id": event_id,
        "transport_status": "SUCCESS",
        "drivers": [g["driver"] for g in transport_groups],
        "passengers": [p for g in transport_groups for p in g["passengers"]],
        "unassigned_passengers": unassigned_passengers,
        "total_selected": len(selected_servers),
        "total_assigned": total_assigned,
        "total_unassigned": len(unassigned_passengers),
    }
