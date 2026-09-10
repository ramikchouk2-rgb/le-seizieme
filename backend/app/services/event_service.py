import math
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_pool
from app.utils.datetime_utils import now_naive_utc
from app.utils.selection_utils import compute_candidate_score
from app.services.selection_engine import haversine_km, normalize_text, serialize_row


async def load_event_detail(event_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.id, e.name, c.name AS city,
                   e.start_datetime, e.end_datetime, e.guest_count,
                   e.alcohol_service, e.food_products_count,
                   e.priority, e.is_urgent, e.status
            FROM events e
            JOIN cities c ON e.city_id = c.id
            WHERE e.id = $1
            LIMIT 1
            """,
            event_id,
        )
        if not row:
            return None
        return serialize_row(dict(row))


async def load_event_requirements_with_counts(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT er.id, er.event_id, er.role_name, er.quantity,
                   er.required_gender, er.minimum_experience, er.minimum_skill_level,
                   COUNT(es.server_id) AS selected
            FROM event_requirements er
            LEFT JOIN event_staff es ON er.event_id = es.event_id
                AND es.role = er.role_name
                AND es.assignment_status IN ('PROPOSED', 'CONFIRMED')
            WHERE er.event_id = $1
            GROUP BY er.id, er.role_name, er.quantity, er.required_gender,
                     er.minimum_experience, er.minimum_skill_level
            ORDER BY er.role_name, er.required_gender
            """,
            event_id,
        )
        result = []
        for r in rows:
            row = serialize_row(dict(r))
            row["missing"] = row["quantity"] - (row["selected"] or 0)
            result.append(row)
        return result


async def load_event_staff_assignments(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT es.id, es.server_id, s.first_name, s.last_name, s.gender,
                   c.name AS city, es.role, es.assignment_status,
                   sp.speed_score, sp.punctuality_score, sp.presentation_score,
                   sp.communication_score, sp.teamwork_score, sp.discipline_score,
                   sp.endurance_score, s.years_experience,
                   sa.status AS availability_status
            FROM event_staff es
            JOIN servers s ON es.server_id = s.id
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_profile sp ON s.id = sp.server_id
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= (
                    SELECT start_datetime FROM events WHERE id = $1
                )
                AND sa.end_datetime >= (
                    SELECT end_datetime FROM events WHERE id = $1
                )
            WHERE es.event_id = $1
            ORDER BY es.assigned_at ASC
            """,
            event_id,
        )
        return [serialize_row(dict(r)) for r in rows]


async def get_event_staff_summary(event_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            """
            SELECT id, name, city_id, start_datetime, end_datetime,
                   guest_count, alcohol_service, food_products_count,
                   priority, is_urgent, status
            FROM events
            WHERE id = $1
            """,
            event_id,
        )
        if not event_row:
            return {"error": "Event not found"}

        event = serialize_row(dict(event_row))
        city_row = await conn.fetchrow(
            "SELECT name FROM cities WHERE id = $1", event["city_id"]
        )
        city_name = city_row["name"] if city_row else ""

        requirements = await load_event_requirements_with_counts(event_id)
        assignments_raw = await load_event_staff_assignments(event_id)

        total_requested = sum(r["quantity"] for r in requirements)
        total_selected = sum(r["selected"] or 0 for r in requirements)
        total_missing = total_requested - total_selected
        percentage = round((total_selected / total_requested) * 100) if total_requested > 0 else 0

        event_start = event["start_datetime"]
        event_end = event["end_datetime"]
        if isinstance(event_start, datetime):
            event_start = event_start.isoformat()
        if isinstance(event_end, datetime):
            event_end = event_end.isoformat()

        event_lat = settings.DEFAULT_EVENT_LATITUDE
        event_lon = settings.DEFAULT_EVENT_LONGITUDE
        city_location = await conn.fetchrow(
            """
            SELECT latitude, longitude FROM server_locations
            WHERE city_id = $1 AND is_current = TRUE
            LIMIT 1
            """,
            event["city_id"],
        )
        if city_location:
            event_lat = float(city_location["latitude"])
            event_lon = float(city_location["longitude"])

        assignments = []
        for a in assignments_raw:
            requirement = next(
                (r for r in requirements if r["role_name"] == a["role"]),
                None,
            )
            min_exp = requirement["minimum_experience"] if requirement else 0
            min_skill = requirement["minimum_skill_level"] if requirement else 1

            candidate = {
                "server_id": a["server_id"],
                "first_name": a["first_name"],
                "last_name": a["last_name"],
                "gender": a["gender"],
                "city": a["city"],
                "role": a["role"],
                "years_experience": a["years_experience"] or 0,
                "availability_status": a["availability_status"] or "AVAILABLE",
                "speed_score": a.get("speed_score"),
                "punctuality_score": a.get("punctuality_score"),
                "presentation_score": a.get("presentation_score"),
                "communication_score": a.get("communication_score"),
                "teamwork_score": a.get("teamwork_score"),
                "discipline_score": a.get("discipline_score"),
                "endurance_score": a.get("endurance_score"),
                "recent_assignments": 0,
            }

            req_for_score = {
                "minimum_experience": min_exp,
                "minimum_skill_level": min_skill,
            }

            score = None
            reasons = []
            try:
                score, reasons = compute_candidate_score(
                    candidate=candidate,
                    requirement=req_for_score,
                    event_start=datetime.fromisoformat(event_start.replace("Z", "+00:00")) if isinstance(event_start, str) else event_start,
                    event_end=datetime.fromisoformat(event_end.replace("Z", "+00:00")) if isinstance(event_end, str) else event_end,
                    event_lat=event_lat,
                    event_lon=event_lon,
                    min_assignments=0,
                    max_assignments=1,
                )
            except Exception:
                score = None
                reasons = []

            assignments.append({
                "id": a["id"],
                "server_id": a["server_id"],
                "server_name": f"{a['first_name']} {a['last_name']}",
                "gender": a["gender"],
                "city": a["city"],
                "role": a["role"],
                "required_gender": None,
                "score": round(score, 1) if score is not None else None,
                "distance_km": candidate.get("distance_km"),
                "years_experience": a["years_experience"] or 0,
                "skill_level": min_skill,
                "availability_status": a["availability_status"] or "AVAILABLE",
                "status": a["assignment_status"],
                "reasons": reasons,
            })

        transport_groups_raw = await conn.fetch(
            """
            SELECT tg.id, tg.driver_server_id, tg.vehicle_id, tg.estimated_distance_km,
                   v.brand, v.model, v.seats_total,
                   s.first_name, s.last_name
            FROM transport_groups tg
            JOIN vehicles v ON tg.vehicle_id = v.id
            JOIN servers s ON tg.driver_server_id = s.id
            WHERE tg.event_id = $1
            ORDER BY tg.created_at ASC
            """,
            event_id,
        )

        transport_groups = []
        for tg in transport_groups_raw:
            passengers_raw = await conn.fetch(
                """
                SELECT tp.server_id, tp.pickup_order, tp.pickup_status,
                       s.first_name, s.last_name, sl.latitude, sl.longitude
                FROM transport_passengers tp
                JOIN servers s ON tp.server_id = s.id
                LEFT JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
                WHERE tp.transport_group_id = $1
                ORDER BY tp.pickup_order ASC
                """,
                tg["id"],
            )
            passengers = []
            for p in passengers_raw:
                passengers.append({
                    "server_id": str(p["server_id"]),
                    "name": f"{p['first_name']} {p['last_name']}".strip(),
                    "pickup_order": p["pickup_order"],
                    "pickup_status": p["pickup_status"],
                    "distance_km": None,
                })
            transport_groups.append({
                "group_id": str(tg["id"]),
                "driver_server_id": str(tg["driver_server_id"]),
                "driver_name": f"{tg['first_name']} {tg['last_name']}".strip(),
                "vehicle": f"{tg['brand']} {tg['model']}",
                "capacity": tg["seats_total"],
                "passenger_count": len(passengers),
                "estimated_distance_km": float(tg["estimated_distance_km"]) if tg["estimated_distance_km"] is not None else None,
                "passengers": passengers,
                "status": "CONFIRMED",
            })

        return {
            "event": {
                "id": str(event["id"]),
                "name": event["name"],
                "city": city_name,
                "start_datetime": event_start,
                "end_datetime": event_end,
                "guest_count": event["guest_count"],
                "alcohol_service": event["alcohol_service"],
                "food_products_count": event["food_products_count"],
                "priority": event["priority"],
                "urgent": event["is_urgent"],
                "status": event["status"],
            },
            "staffing": {
                "requested": total_requested,
                "selected": total_selected,
                "missing": total_missing,
                "percentage": percentage,
            },
            "requirements": requirements,
            "assignments": assignments,
            "transport": {
                "groups": transport_groups,
                "total_groups": len(transport_groups),
                "total_passengers": sum(g["passenger_count"] for g in transport_groups),
            },
        }


async def confirm_staff_assignments(
    event_id: str,
    assignments: list[dict[str, str]],
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=400,
                    detail="L'événement ne peut pas recevoir d'affectations dans son état actuel.",
                )

            requirements = await conn.fetch(
                """
                SELECT id, role_name, quantity, required_gender,
                       minimum_experience, minimum_skill_level
                FROM event_requirements
                WHERE event_id = $1
                """,
                event_id,
            )
            req_by_role: dict[str, list[dict[str, Any]]] = {}
            req_total_qty: dict[str, int] = {}
            for r in requirements:
                role_name = r["role_name"]
                req_by_role.setdefault(role_name, []).append({
                    "id": str(r["id"]),
                    "quantity": r["quantity"],
                    "required_gender": r["required_gender"],
                    "minimum_experience": r["minimum_experience"],
                    "minimum_skill_level": r["minimum_skill_level"],
                })
                req_total_qty[role_name] = req_total_qty.get(role_name, 0) + r["quantity"]

            server_ids = [a["server_id"] for a in assignments]
            if len(set(server_ids)) != len(server_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Un serveur ne peut être affecté qu'une seule fois.",
                )

            servers = await conn.fetch(
                "SELECT id, is_active, gender, years_experience, first_name, last_name FROM servers WHERE id = ANY($1::uuid[])",
                server_ids,
            )
            server_map: dict[str, dict[str, Any]] = {str(s["id"]): dict(s) for s in servers}

            skill_rows = await conn.fetch(
                """
                SELECT ss.server_id, s.name AS skill_name, ss.level
                FROM server_skills ss
                JOIN skills s ON ss.skill_id = s.id
                WHERE ss.server_id = ANY($1::uuid[])
                """,
                server_ids,
            )
            server_skills_map: dict[str, dict[str, int]] = {}
            for sk in skill_rows:
                sid = str(sk["server_id"])
                skill_name = normalize_text(sk["skill_name"].lower())
                server_skills_map.setdefault(sid, {})
                server_skills_map[sid][skill_name] = max(
                    server_skills_map[sid].get(skill_name, 0), sk["level"]
                )

            for assignment in assignments:
                server_id = assignment["server_id"]
                role = assignment["role"]

                if server_id not in server_map:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Serveur introuvable: {server_id}",
                    )

                server = server_map[server_id]
                if not server["is_active"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Serveur inactif: {server_id}",
                    )

                role_requirements = req_by_role.get(role)
                if not role_requirements:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Exigence introuvable pour le rôle: {role}",
                    )

                matching_req = None
                for req in role_requirements:
                    if req["required_gender"] and server["gender"] != req["required_gender"]:
                        continue
                    if (server["years_experience"] or 0) < req["minimum_experience"]:
                        continue
                    matching_req = req
                    break

                if not matching_req:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Genre incorrect pour le rôle {role}",
                    )

                server_skills = server_skills_map.get(str(server_id), {})
                max_level = server_skills.get(normalize_text(role.lower()), 0)
                if max_level < matching_req["minimum_skill_level"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Niveau de compétence insuffisant pour le rôle {role}",
                    )

                event_start_row = await conn.fetchrow(
                    "SELECT start_datetime, end_datetime FROM events WHERE id = $1",
                    event_id,
                )
                event_start = event_start_row["start_datetime"]
                event_end = event_start_row["end_datetime"]

                avail_row = await conn.fetchrow(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM server_availability sa
                    WHERE sa.server_id = $1
                      AND sa.start_datetime <= $2
                      AND sa.end_datetime >= $3
                      AND sa.status = 'AVAILABLE'
                    """,
                    server_id,
                    event_start,
                    event_end,
                )
                if not avail_row or avail_row["cnt"] == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Serveur non disponible pendant l'événement: {server_id}",
                    )

                existing = await conn.fetchrow(
                    "SELECT id FROM event_staff WHERE event_id = $1 AND server_id = $2",
                    event_id,
                    server_id,
                )
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Serveur déjà affecté à cet événement: {server_id}",
                    )

                selected_count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM event_staff
                    WHERE event_id = $1
                      AND role = $2
                      AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                    """,
                    event_id,
                    role,
                )
                if selected_count >= req_total_qty.get(role, 0):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Poste déjà complet pour le rôle: {role}",
                    )

            created = []
            for assignment in assignments:
                server_id = assignment["server_id"]
                role = assignment["role"]
                server = server_map[server_id]
                row = await conn.fetchrow(
                    """
                    INSERT INTO event_staff (event_id, server_id, role, assignment_status, confirmed_at)
                    VALUES ($1, $2, $3, 'CONFIRMED', NOW())
                    RETURNING id, event_id, server_id, role, assignment_status, assigned_at, confirmed_at
                    """,
                    event_id,
                    server_id,
                    role,
                )
                created.append(
                    {
                        "server_id": str(row["server_id"]),
                        "server_name": f"{server['first_name']} {server['last_name']}".strip(),
                        "role": row["role"],
                    }
                )

            total_requested_row = await conn.fetchrow(
                "SELECT COALESCE(SUM(quantity), 0) AS total FROM event_requirements WHERE event_id = $1",
                event_id,
            )
            total_selected_row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total
                FROM event_staff
                WHERE event_id = $1
                  AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                """,
                event_id,
            )
            total_requested = total_requested_row["total"]
            total_selected = total_selected_row["total"]
            missing_positions = max(0, total_requested - total_selected)

            return {
                "event_id": event_id,
                "status": "CONFIRMED",
                "created_count": len(created),
                "assignments": created,
                "missing_positions": missing_positions,
            }


async def confirm_transport(event_id: str, groups: list[dict[str, Any]]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status, start_datetime, end_datetime FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=400,
                    detail="L'événement ne peut pas recevoir de transport dans son état actuel.",
                )

            event_start = event_row["start_datetime"]
            event_end = event_row["end_datetime"]

            driver_ids = [g["driver_server_id"] for g in groups]
            passenger_ids = []
            for g in groups:
                for p in g.get("passengers", []):
                    passenger_ids.append(p["server_id"])

            all_server_ids = list(set(driver_ids + passenger_ids))
            if not all_server_ids:
                raise HTTPException(status_code=400, detail="Aucun serveur spécifié.")

            servers = await conn.fetch(
                "SELECT id, is_active, gender, years_experience, first_name, last_name FROM servers WHERE id = ANY($1::uuid[])",
                all_server_ids,
            )
            server_map: dict[str, dict[str, Any]] = {str(s["id"]): dict(s) for s in servers}

            event_staff_rows = await conn.fetch(
                """
                SELECT server_id, role, assignment_status
                FROM event_staff
                WHERE event_id = $1
                  AND server_id = ANY($2::uuid[])
                  AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                """,
                event_id,
                all_server_ids,
            )
            assigned_server_ids = {str(r["server_id"]) for r in event_staff_rows}

            for g in groups:
                driver_id = g["driver_server_id"]
                if driver_id not in assigned_server_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le chauffeur {driver_id} n'est pas assigné à cet événement.",
                    )

            for pid in passenger_ids:
                if pid not in assigned_server_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le passager {pid} n'est pas assigné à cet événement.",
                    )

            for g in groups:
                driver_id = g["driver_server_id"]
                if driver_id not in server_map:
                    raise HTTPException(status_code=404, detail=f"Chauffeur introuvable: {driver_id}")

                driver_server = server_map[driver_id]
                if not driver_server["is_active"]:
                    raise HTTPException(status_code=400, detail=f"Chauffeur inactif: {driver_id}")

                vehicle_row = await conn.fetchrow(
                    """
                    SELECT v.id, v.vehicle_type, v.brand, v.model, v.seats_total, v.can_transport_coworkers, v.is_active
                    FROM vehicles v
                    WHERE v.owner_server_id = $1
                      AND v.is_active = TRUE
                      AND v.can_transport_coworkers = TRUE
                    """,
                    driver_id,
                )
                if not vehicle_row:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le chauffeur {driver_id} n'a pas de véhicule actif autorisé pour le transport de collègues.",
                    )

                vehicle_avail = await conn.fetchrow(
                    """
                    SELECT available
                    FROM vehicle_availability
                    WHERE vehicle_id = $1
                      AND start_datetime <= $2
                      AND end_datetime >= $3
                    ORDER BY start_datetime DESC
                    LIMIT 1
                    """,
                    vehicle_row["id"],
                    event_start,
                    event_end,
                )
                if vehicle_avail is not None and not vehicle_avail["available"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le véhicule du chauffeur {driver_id} n'est pas disponible pendant l'événement.",
                    )

                capacity = vehicle_row["seats_total"] - 1
                passengers = g.get("passengers", [])
                if len(passengers) > capacity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le véhicule de {driver_server['first_name']} {driver_server['last_name']} ne peut transporter que {capacity} passagers.",
                    )

            server_ids_in_groups: set[str] = set()
            for g in groups:
                driver_id = g["driver_server_id"]
                if driver_id in server_ids_in_groups:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le serveur {driver_id} est déjà défini comme chauffeur dans un autre groupe.",
                    )
                server_ids_in_groups.add(driver_id)

                for p in g.get("passengers", []):
                    pid = p["server_id"]
                    if pid == driver_id:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Le chauffeur {driver_id} ne peut pas être son propre passager.",
                        )
                    if pid in server_ids_in_groups:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Le serveur {pid} est déjà affecté à un autre groupe de transport.",
                        )
                    server_ids_in_groups.add(pid)

            locations = await conn.fetch(
                """
                SELECT server_id, latitude, longitude, is_verified
                FROM server_locations
                WHERE server_id = ANY($1::uuid[])
                  AND is_current = TRUE
                """,
                all_server_ids,
            )
            location_map: dict[str, dict[str, Any]] = {str(r["server_id"]): dict(r) for r in locations}

            avail_rows = await conn.fetch(
                """
                SELECT sa.server_id, COUNT(*) AS cnt
                FROM server_availability sa
                WHERE sa.server_id = ANY($1::uuid[])
                  AND sa.start_datetime <= $2
                  AND sa.end_datetime >= $3
                  AND sa.status = 'AVAILABLE'
                GROUP BY sa.server_id
                """,
                all_server_ids,
                event_start,
                event_end,
            )
            available_set = {str(r["server_id"]) for r in avail_rows if r["cnt"] > 0}

            for g in groups:
                driver_id = g["driver_server_id"]
                driver_loc = location_map.get(driver_id)
                if not driver_loc or not driver_loc["is_verified"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le chauffeur {driver_id} n'a pas de localisation vérifiée.",
                    )

                driver_lat = float(driver_loc["latitude"])
                driver_lon = float(driver_loc["longitude"])

                if driver_id not in available_set:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Le chauffeur {driver_id} n'est pas disponible pendant l'événement.",
                    )

                passengers = g.get("passengers", [])
                validated_passengers = []
                for p in passengers:
                    pid = p["server_id"]
                    passenger_loc = location_map.get(pid)
                    if not passenger_loc or not passenger_loc["is_verified"]:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Le passager {pid} n'a pas de localisation vérifiée.",
                        )

                    if pid not in available_set:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Le passager {pid} n'est pas disponible pendant l'événement.",
                        )

                    passenger_lat = float(passenger_loc["latitude"])
                    passenger_lon = float(passenger_loc["longitude"])
                    distance = haversine_km(driver_lat, driver_lon, passenger_lat, passenger_lon)
                    if distance > 20:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Le passager {pid} est trop loin du chauffeur ({round(distance, 1)} km > 20 km).",
                        )
                    validated_passengers.append({**p, "distance_km": distance, "latitude": passenger_lat, "longitude": passenger_lon})

                validated_passengers.sort(key=lambda x: x["distance_km"])
                for idx, p in enumerate(validated_passengers, start=1):
                    p["pickup_order"] = idx

                g["validated_passengers"] = validated_passengers
                g["driver_latitude"] = driver_lat
                g["driver_longitude"] = driver_lon
                g["vehicle_id"] = str(vehicle_row["id"])
                g["vehicle_label"] = f"{vehicle_row['brand']} {vehicle_row['model']}"
                g["capacity"] = vehicle_row["seats_total"]

            existing_groups = await conn.fetch(
                """
                SELECT tg.id, tg.driver_server_id, tg.vehicle_id, tg.estimated_distance_km,
                       v.brand, v.model, v.seats_total,
                       s.first_name, s.last_name
                FROM transport_groups tg
                JOIN vehicles v ON tg.vehicle_id = v.id
                JOIN servers s ON tg.driver_server_id = s.id
                WHERE tg.event_id = $1
                """,
                event_id,
            )
            existing_driver_ids = {str(r["driver_server_id"]) for r in existing_groups}
            existing_group_map = {str(r["driver_server_id"]): str(r["id"]) for r in existing_groups}

            if existing_driver_ids:
                created_groups = []
                created_passengers = 0
                for row in existing_groups:
                    driver_id = str(row["driver_server_id"])
                    group_id = str(row["id"])
                    passenger_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM transport_passengers WHERE transport_group_id = $1",
                        group_id,
                    )
                    driver_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                    created_groups.append({
                        "group_id": group_id,
                        "driver_name": driver_name,
                        "vehicle": f"{row.get('brand', '')} {row.get('model', '')}".strip(),
                        "capacity": row.get("seats_total", 0),
                        "passenger_count": passenger_count or 0,
                        "estimated_distance_km": float(row["estimated_distance_km"]) if row["estimated_distance_km"] is not None else None,
                    })
                    created_passengers += passenger_count or 0
                return {
                    "event_id": event_id,
                    "status": "CONFIRMED",
                    "groups_created": 0,
                    "passengers_created": created_passengers,
                    "groups": created_groups,
                    "message": "Le transport de cet événement est déjà confirmé.",
                }

            created_groups = []
            total_passengers = 0
            for g in groups:
                driver_id = g["driver_server_id"]
                driver_server = server_map[driver_id]
                driver_name = f"{driver_server.get('first_name', '')} {driver_server.get('last_name', '')}".strip()
                group_row = await conn.fetchrow(
                    """
                    INSERT INTO transport_groups (
                        event_id, vehicle_id, driver_server_id,
                        departure_latitude, departure_longitude, departure_location_label,
                        departure_time, destination_latitude, destination_longitude, destination_label,
                        estimated_distance_km, estimated_duration_minutes, status
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'CONFIRMED')
                    RETURNING id
                    """,
                    event_id,
                    g["vehicle_id"],
                    driver_id,
                    g["driver_latitude"],
                    g["driver_longitude"],
                    f"Depart {driver_name}",
                    event_start,
                    g["driver_latitude"],
                    g["driver_longitude"],
                    "Destination",
                    round(sum(p["distance_km"] for p in g["validated_passengers"]), 2) if g["validated_passengers"] else 0,
                    round(sum(p["distance_km"] for p in g["validated_passengers"]) * 2) if g["validated_passengers"] else 0,
                )
                group_id = group_row["id"]

                for p in g["validated_passengers"]:
                    passenger_loc = location_map.get(p["server_id"], {})
                    await conn.execute(
                        """
                        INSERT INTO transport_passengers (
                            transport_group_id, server_id,
                            pickup_latitude, pickup_longitude, pickup_location_label,
                            pickup_order, pickup_status
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, 'PENDING')
                        """,
                        group_id,
                        p["server_id"],
                        passenger_loc.get("latitude"),
                        passenger_loc.get("longitude"),
                        f"Pickup {p['server_id']}",
                        p["pickup_order"],
                    )
                    total_passengers += 1

                created_groups.append({
                    "group_id": str(group_id),
                    "driver_name": driver_name,
                    "vehicle": g["vehicle_label"],
                    "capacity": g["capacity"],
                    "passenger_count": len(g["validated_passengers"]),
                    "estimated_distance_km": round(sum(p["distance_km"] for p in g["validated_passengers"]), 2) if g["validated_passengers"] else 0,
                })

            return {
                "event_id": event_id,
                "status": "CONFIRMED",
                "groups_created": len(created_groups),
                "passengers_created": total_passengers,
                "groups": created_groups,
                "message": None,
            }


SORT_WHITELIST = {
    "name": "e.name",
    "city": "c.name",
    "date": "e.start_datetime",
    "guests": "e.guest_count",
    "status": "e.status",
    "staffing": "staffing_percentage",
    "priority": "e.priority",
    "urgent": "e.is_urgent",
}


async def load_event_list(
    search: str | None,
    city: str | None,
    status: str | None,
    priority: str | None,
    urgent: bool | None,
    staffing: str | None,
    date_range: str | None,
    sort_by: str | None,
    sort_order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_clauses: list[str] = []
        params: list[Any] = []
        idx = 1

        if search:
            where_clauses.append(
                f"(e.name ILIKE ${idx} OR c.name ILIKE ${idx})"
            )
            params.append(f"%{search}%")
            idx += 1

        if city:
            where_clauses.append(f"c.name = ${idx}")
            params.append(city)
            idx += 1

        if status:
            where_clauses.append(f"e.status = ${idx}")
            params.append(status)
            idx += 1

        if priority:
            where_clauses.append(f"e.priority = ${idx}")
            params.append(priority)
            idx += 1

        if urgent is not None:
            where_clauses.append(f"e.is_urgent = ${idx}")
            params.append(urgent)
            idx += 1

        if date_range:
            now = now_naive_utc()
            if date_range == "UPCOMING":
                where_clauses.append(f"e.start_datetime > ${idx}")
                params.append(now)
            elif date_range == "TODAY":
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow_start = today_start + timedelta(days=1)
                where_clauses.append(f"e.start_datetime >= ${idx}")
                params.append(today_start)
                where_clauses.append(f"e.start_datetime < ${idx + 1}")
                params.append(tomorrow_start)
                idx += 2
            elif date_range == "PAST":
                where_clauses.append(f"e.start_datetime <= ${idx}")
                params.append(now)
            idx += 1

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        order_column = SORT_WHITELIST.get(sort_by, "e.start_datetime")
        order_direction = "ASC" if sort_order == "asc" else "DESC"

        if staffing == "complete":
            having_sql = "HAVING SUM(er.quantity) = COUNT(es.server_id)"
        elif staffing == "incomplete":
            having_sql = "HAVING COUNT(es.server_id) < SUM(er.quantity) OR COUNT(es.server_id) IS NULL"
        else:
            having_sql = ""

        count_query = f"""
            SELECT COUNT(DISTINCT e.id) AS total
            FROM events e
            JOIN cities c ON e.city_id = c.id
            LEFT JOIN event_requirements er ON e.id = er.event_id
            LEFT JOIN event_staff es ON e.id = es.event_id
                AND es.assignment_status IN ('PROPOSED', 'CONFIRMED')
            WHERE {where_sql}
            {having_sql}
        """

        total_row = await conn.fetchrow(count_query, *params)
        total = total_row["total"] if total_row else 0

        data_query = f"""
            SELECT
                e.id,
                e.name,
                c.name AS city,
                e.start_datetime,
                e.end_datetime,
                e.guest_count,
                e.alcohol_service,
                e.food_products_count,
                e.priority,
                e.is_urgent,
                e.status,
                COALESCE(SUM(er.quantity), 0) AS requested,
                COUNT(es.server_id) AS selected,
                COALESCE(SUM(er.quantity), 0) - COUNT(es.server_id) AS missing,
                CASE
                    WHEN COALESCE(SUM(er.quantity), 0) > 0
                    THEN ROUND((COUNT(es.server_id)::numeric / COALESCE(SUM(er.quantity), 0)) * 100)
                    ELSE 0
                END AS staffing_percentage
            FROM events e
            JOIN cities c ON e.city_id = c.id
            LEFT JOIN event_requirements er ON e.id = er.event_id
            LEFT JOIN event_staff es ON e.id = es.event_id
                AND es.assignment_status IN ('PROPOSED', 'CONFIRMED')
            WHERE {where_sql}
            GROUP BY e.id, c.name, e.name, e.start_datetime, e.end_datetime,
                     e.guest_count, e.alcohol_service, e.food_products_count,
                     e.priority, e.is_urgent, e.status
            {having_sql}
            ORDER BY {order_column} {order_direction}, e.id ASC
            LIMIT ${idx} OFFSET ${idx + 1}
        """

        params.extend([page_size, (page - 1) * page_size])
        rows = await conn.fetch(data_query, *params)

        result = []
        for r in rows:
            result.append({
                "id": str(r["id"]),
                "name": r["name"],
                "city": r["city"],
                "start_datetime": r["start_datetime"].isoformat() if isinstance(r["start_datetime"], datetime) else str(r["start_datetime"]),
                "end_datetime": r["end_datetime"].isoformat() if isinstance(r["end_datetime"], datetime) else str(r["end_datetime"]),
                "guest_count": r["guest_count"],
                "alcohol_service": r["alcohol_service"],
                "food_products_count": r["food_products_count"],
                "priority": r["priority"],
                "urgent": r["is_urgent"],
                "status": r["status"],
                "staffing": {
                    "requested": r["requested"],
                    "selected": r["selected"],
                    "missing": r["missing"],
                    "percentage": r["staffing_percentage"],
                },
            })

        return result, total


async def load_event_stats() -> dict[str, int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = now_naive_utc()

        upcoming_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS count
            FROM events
            WHERE start_datetime > $1
            """,
            now,
        )

        planned_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS count
            FROM events
            WHERE status = 'PLANNED'
            """
        )

        urgent_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS count
            FROM events
            WHERE is_urgent = TRUE
            """
        )

        missing_row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(req.total_quantity) - COUNT(staff.server_id), 0) AS missing
            FROM events e
            LEFT JOIN (
                SELECT event_id, SUM(quantity) AS total_quantity
                FROM event_requirements
                GROUP BY event_id
            ) req ON e.id = req.event_id
            LEFT JOIN event_staff staff ON e.id = staff.event_id
                AND staff.assignment_status IN ('PROPOSED', 'CONFIRMED')
            """
        )

        return {
            "upcoming_events": upcoming_row["count"] if upcoming_row else 0,
            "planned_events": planned_row["count"] if planned_row else 0,
            "urgent_events": urgent_row["count"] if urgent_row else 0,
            "missing_positions": missing_row["missing"] if missing_row else 0,
        }


async def create_event(data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        start_datetime = datetime.fromisoformat(data["start_datetime"].replace("Z", "+00:00")) if isinstance(data["start_datetime"], str) else data["start_datetime"]
        end_datetime = datetime.fromisoformat(data["end_datetime"].replace("Z", "+00:00")) if isinstance(data["end_datetime"], str) else data["end_datetime"]

        row = await conn.fetchrow(
            """
            INSERT INTO events (
                name, client_name, city_id, address,
                start_datetime, end_datetime, guest_count, event_type,
                alcohol_service, food_products_count,
                priority, is_urgent, required_response_minutes,
                status, notes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING id, name, client_name, city_id, address,
                      start_datetime, end_datetime, guest_count, event_type,
                      alcohol_service, food_products_count,
                      priority, is_urgent, required_response_minutes,
                      status, notes, created_at, updated_at
            """,
            data["name"],
            data["client_name"],
            data["city_id"],
            data["address"],
            start_datetime,
            end_datetime,
            data["guest_count"],
            data["event_type"],
            data.get("alcohol_service", False),
            data.get("food_products_count", 0),
            data.get("priority", "NORMAL"),
            data.get("is_urgent", False),
            data.get("required_response_minutes"),
            data.get("status", "PLANNED"),
            data.get("notes"),
        )
        return dict(row)


async def load_cities() -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name
            FROM cities
            ORDER BY name ASC
            """
        )
        return [dict(r) for r in rows]


async def create_requirement(event_id: str, data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT id FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")

        if data.get("quantity", 1) < 1:
            raise HTTPException(status_code=422, detail="La quantité doit être au moins 1.")
        skill = data.get("minimum_skill_level", 1)
        if skill < 1 or skill > 10:
            raise HTTPException(status_code=422, detail="Le niveau de compétence doit être entre 1 et 10.")
        if data.get("minimum_experience", 0) < 0:
            raise HTTPException(status_code=422, detail="L'expérience ne peut pas être négative.")
        gender = data.get("required_gender")
        if gender is not None and gender not in ("MALE", "FEMALE", "OTHER"):
            raise HTTPException(status_code=422, detail="Genre invalide.")

        row = await conn.fetchrow(
            """
            INSERT INTO event_requirements (
                event_id, role_name, quantity,
                required_gender, minimum_experience, minimum_skill_level, notes
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, event_id, role_name, quantity,
                      required_gender, minimum_experience, minimum_skill_level, notes
            """,
            event_id,
            data["role_name"],
            data["quantity"],
            data.get("required_gender"),
            data.get("minimum_experience", 0),
            data.get("minimum_skill_level", 1),
            data.get("notes"),
        )
        result = dict(row)
        result["selected"] = 0
        result["missing"] = result["quantity"]
        result["requirement_id"] = str(result.pop("id"))
        return result


async def update_requirement(event_id: str, requirement_id: str, data: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT status FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")
        if event_row["status"] in ("CANCELLED", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail="L'événement ne peut pas être modifié dans son état actuel.",
            )

        req_row = await conn.fetchrow(
            "SELECT id, role_name, quantity FROM event_requirements WHERE id = $1 AND event_id = $2",
            requirement_id,
            event_id,
        )
        if not req_row:
            raise HTTPException(status_code=404, detail="Poste introuvable.")

        confirmed_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM event_staff
            WHERE event_id = $1
              AND role = $2
              AND assignment_status IN ('CONFIRMED')
            """,
            event_id,
            req_row["role_name"],
        )

        new_quantity = data.get("quantity", req_row["quantity"])
        if confirmed_count > new_quantity:
            raise HTTPException(
                status_code=400,
                detail="Cette modification est impossible car des serveurs sont déjà confirmés pour ce poste.",
            )

        new_role = data.get("role_name", req_row["role_name"])
        if new_role != req_row["role_name"]:
            role_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM event_staff
                WHERE event_id = $1
                  AND role = $2
                  AND assignment_status IN ('CONFIRMED')
                """,
                event_id,
                req_row["role_name"],
            )
            if role_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Impossible de modifier le rôle : des serveurs sont déjà confirmés pour ce poste.",
                )

        updates = []
        values = []

        allowed_fields = {
            "role_name": "role_name",
            "quantity": "quantity",
            "minimum_skill_level": "minimum_skill_level",
            "minimum_experience": "minimum_experience",
            "required_gender": "required_gender",
        }

        for key, column in allowed_fields.items():
            if key in data:
                updates.append(f"{column} = ${len(values) + 2}")
                values.append(data[key])

        if not updates:
            result = dict(req_row)
            result["selected"] = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM event_staff
                WHERE event_id = $1
                  AND role = $2
                  AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                """,
                event_id,
                req_row["role_name"],
            )
            result["missing"] = result["quantity"] - (result["selected"] or 0)
            result["requirement_id"] = str(result.pop("id"))
            return result

        await conn.execute(
            f"""
            UPDATE event_requirements
            SET {', '.join(updates)}
            WHERE id = ${len(values) + 2} AND event_id = ${len(values) + 3}
            """,
            *values,
            requirement_id,
            event_id,
        )

        updated_row = await conn.fetchrow(
            """
            SELECT id, role_name, quantity, minimum_skill_level, minimum_experience, required_gender
            FROM event_requirements
            WHERE id = $1 AND event_id = $2
            """,
            requirement_id,
            event_id,
        )

        result = dict(updated_row)
        result["selected"] = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM event_staff
            WHERE event_id = $1
              AND role = $2
              AND assignment_status IN ('PROPOSED', 'CONFIRMED')
            """,
            event_id,
            result["role_name"],
        )
        result["missing"] = result["quantity"] - (result["selected"] or 0)
        result["requirement_id"] = str(result.pop("id"))
        return result


async def delete_requirement(event_id: str, requirement_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT status FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")
        if event_row["status"] in ("CANCELLED", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail="L'événement ne peut pas être modifié dans son état actuel.",
            )

        req_row = await conn.fetchrow(
            "SELECT id, role_name FROM event_requirements WHERE id = $1 AND event_id = $2",
            requirement_id,
            event_id,
        )
        if not req_row:
            raise HTTPException(status_code=404, detail="Poste introuvable.")

        confirmed_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM event_staff
            WHERE event_id = $1
              AND role = $2
              AND assignment_status IN ('CONFIRMED')
            """,
            event_id,
            req_row["role_name"],
        )

        if confirmed_count > 0:
            raise HTTPException(
                status_code=409,
                detail="Impossible de supprimer ce poste : des serveurs sont déjà confirmés.",
            )

        await conn.execute(
            "DELETE FROM event_requirements WHERE id = $1 AND event_id = $2",
            requirement_id,
            event_id,
        )

        return {"deleted": True}


async def add_staff_assignment(event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=400,
                    detail="L'événement ne peut pas recevoir d'affectations dans son état actuel.",
                )

            server_id = payload["server_id"]
            role = payload["role"]
            requirement_id = payload["requirement_id"]

            server_row = await conn.fetchrow(
                "SELECT id, is_active, gender, years_experience, first_name, last_name FROM servers WHERE id = $1",
                server_id,
            )
            if not server_row:
                raise HTTPException(status_code=404, detail="Serveur introuvable.")
            if not server_row["is_active"]:
                raise HTTPException(status_code=400, detail="Serveur inactif.")

            req_row = await conn.fetchrow(
                "SELECT id, role_name, quantity, required_gender, minimum_experience, minimum_skill_level FROM event_requirements WHERE id = $1 AND event_id = $2",
                requirement_id,
                event_id,
            )
            if not req_row:
                raise HTTPException(status_code=404, detail="Exigence introuvable.")
            if req_row["role_name"] != role:
                raise HTTPException(
                    status_code=400,
                    detail="Le rôle ne correspond pas à l'exigence sélectionnée.",
                )

            if req_row["required_gender"] and server_row["gender"] != req_row["required_gender"]:
                raise HTTPException(
                    status_code=400,
                    detail="Genre incorrect pour ce poste.",
                )

            if (server_row["years_experience"] or 0) < req_row["minimum_experience"]:
                raise HTTPException(
                    status_code=400,
                    detail="Expérience insuffisante pour ce poste.",
                )

            skill_rows = await conn.fetch(
                """
                SELECT s.name AS skill_name, ss.level
                FROM server_skills ss
                JOIN skills s ON ss.skill_id = s.id
                WHERE ss.server_id = $1
                """,
                server_id,
            )
            max_level = 0
            for sk in skill_rows:
                if normalize_text(sk["skill_name"].lower()) == normalize_text(role.lower()):
                    max_level = max(max_level, sk["level"])
            if max_level < req_row["minimum_skill_level"]:
                raise HTTPException(
                    status_code=400,
                    detail="Niveau de compétence insuffisant pour ce poste.",
                )

            event_start_row = await conn.fetchrow(
                "SELECT start_datetime, end_datetime FROM events WHERE id = $1",
                event_id,
            )
            event_start = event_start_row["start_datetime"]
            event_end = event_start_row["end_datetime"]

            avail_row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS cnt
                FROM server_availability sa
                WHERE sa.server_id = $1
                  AND sa.start_datetime <= $2
                  AND sa.end_datetime >= $3
                  AND sa.status = 'AVAILABLE'
                """,
                server_id,
                event_start,
                event_end,
            )
            if not avail_row or avail_row["cnt"] == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Serveur non disponible pendant l'événement.",
                )

            existing = await conn.fetchrow(
                "SELECT id FROM event_staff WHERE event_id = $1 AND server_id = $2",
                event_id,
                server_id,
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="Ce serveur est déjà affecté à cet événement.",
                )

            selected_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM event_staff
                WHERE event_id = $1
                  AND role = $2
                  AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                """,
                event_id,
                role,
            )
            if selected_count >= req_row["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail="Poste déjà complet pour ce rôle.",
                )

            row = await conn.fetchrow(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status)
                VALUES ($1, $2, $3, 'PROPOSED')
                RETURNING id, event_id, server_id, role, assignment_status, assigned_at, confirmed_at
                """,
                event_id,
                server_id,
                role,
            )
            result = serialize_row(dict(row))
            result["server_name"] = f"{server_row['first_name']} {server_row['last_name']}".strip()
            result["gender"] = server_row["gender"]
            result["city"] = ""
            result["score"] = None
            result["distance_km"] = None
            result["years_experience"] = server_row["years_experience"]
            result["skill_level"] = max_level
            result["availability_status"] = "AVAILABLE"
            result["requirement_id"] = requirement_id
            result["status"] = result.pop("assignment_status")
            return result


async def remove_staff_assignment(event_id: str, assignment_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=400,
                    detail="L'événement ne peut pas être modifié dans son état actuel.",
                )

            assignment_row = await conn.fetchrow(
                "SELECT id, event_id, server_id, role, assignment_status FROM event_staff WHERE id = $1 AND event_id = $2",
                assignment_id,
                event_id,
            )
            if not assignment_row:
                raise HTTPException(status_code=404, detail="Affectation introuvable.")

            if assignment_row["assignment_status"] == "CONFIRMED":
                raise HTTPException(
                    status_code=409,
                    detail="Cette affectation est confirmée et ne peut pas être supprimée directement.",
                )

            await conn.execute(
                "DELETE FROM event_staff WHERE id = $1 AND event_id = $2",
                assignment_id,
                event_id,
            )

            return {"deleted": True}


async def update_staff_assignment(event_id: str, assignment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT status FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")
            if event_row["status"] in ("CANCELLED", "COMPLETED"):
                raise HTTPException(
                    status_code=400,
                    detail="L'événement ne peut pas être modifié dans son état actuel.",
                )

            assignment_row = await conn.fetchrow(
                "SELECT id, event_id, server_id, role, assignment_status FROM event_staff WHERE id = $1 AND event_id = $2",
                assignment_id,
                event_id,
            )
            if not assignment_row:
                raise HTTPException(status_code=404, detail="Affectation introuvable.")

            if assignment_row["assignment_status"] == "CONFIRMED":
                raise HTTPException(
                    status_code=409,
                    detail="Cette affectation est confirmée et ne peut pas être modifiée directement.",
                )

            updates = {}
            if "role" in payload:
                new_role = payload["role"]
                req_row = await conn.fetchrow(
                    "SELECT id, quantity, required_gender, minimum_experience, minimum_skill_level FROM event_requirements WHERE id = $1 AND event_id = $2",
                    payload.get("requirement_id"),
                    event_id,
                )
                if not req_row:
                    raise HTTPException(status_code=404, detail="Exigence introuvable.")
                if req_row["role_name"] != new_role:
                    raise HTTPException(
                        status_code=400,
                        detail="Le rôle ne correspond pas à l'exigence sélectionnée.",
                    )

                server_row = await conn.fetchrow(
                    "SELECT gender, years_experience FROM servers WHERE id = $1",
                    assignment_row["server_id"],
                )
                if req_row["required_gender"] and server_row["gender"] != req_row["required_gender"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Genre incorrect pour ce poste.",
                    )
                if (server_row["years_experience"] or 0) < req_row["minimum_experience"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Expérience insuffisante pour ce poste.",
                    )

                skill_rows = await conn.fetch(
                    """
                    SELECT s.name AS skill_name, ss.level
                    FROM server_skills ss
                    JOIN skills s ON ss.skill_id = s.id
                    WHERE ss.server_id = $1
                    """,
                    assignment_row["server_id"],
                )
                max_level = 0
                for sk in skill_rows:
                    if normalize_text(sk["skill_name"].lower()) == normalize_text(new_role.lower()):
                        max_level = max(max_level, sk["level"])
                if max_level < req_row["minimum_skill_level"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Niveau de compétence insuffisant pour ce poste.",
                    )

                selected_count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM event_staff
                    WHERE event_id = $1
                      AND role = $2
                      AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                      AND id != $3
                    """,
                    event_id,
                    new_role,
                    assignment_id,
                )
                if selected_count >= req_row["quantity"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Poste déjà complet pour ce rôle.",
                    )

                updates["role"] = new_role

            if "assignment_status" in payload:
                new_status = payload["assignment_status"]
                if new_status not in ("PROPOSED", "CONFIRMED", "DECLINED", "CANCELLED", "COMPLETED"):
                    raise HTTPException(status_code=400, detail="Statut d'affectation invalide.")
                if new_status == "CONFIRMED":
                    raise HTTPException(
                        status_code=400,
                        detail="Le statut CONFIRMED ne peut pas être appliqué directement. Utilisez l'endpoint de confirmation.",
                    )
                updates["assignment_status"] = new_status
                if new_status == "CONFIRMED":
                    updates["confirmed_at"] = datetime.now()
                elif "confirmed_at" in updates:
                    updates.pop("confirmed_at")

            if not updates:
                return serialize_row(dict(assignment_row))

            set_clause = ", ".join(f"{k} = ${i + 3}" for i, k in enumerate(updates.keys()))
            values = [assignment_id, event_id] + list(updates.values())

            await conn.execute(
                f"""
                UPDATE event_staff
                SET {set_clause}
                WHERE id = $1 AND event_id = $2
                """,
                *values,
            )

            updated_row = await conn.fetchrow(
                "SELECT id, event_id, server_id, role, assignment_status, assigned_at, confirmed_at FROM event_staff WHERE id = $1 AND event_id = $2",
                assignment_id,
                event_id,
            )
            result = serialize_row(dict(updated_row))
            result["server_name"] = ""
            result["gender"] = None
            result["city"] = None
            result["score"] = None
            result["distance_km"] = None
            result["years_experience"] = None
            result["skill_level"] = None
            result["availability_status"] = None
            result["status"] = result.pop("assignment_status")
            return result


async def get_eligible_staff(event_id: str, search: str | None = None, role: str | None = None) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT start_datetime, end_datetime FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")

        event_start = event_row["start_datetime"]
        event_end = event_row["end_datetime"]

        requirements = await conn.fetch(
            """
            SELECT id, role_name, quantity, required_gender, minimum_experience, minimum_skill_level
            FROM event_requirements
            WHERE event_id = $1
            """,
            event_id,
        )
        req_by_role: dict[str, list[dict[str, Any]]] = {}
        for r in requirements:
            req_by_role.setdefault(r["role_name"], []).append({
                "id": str(r["id"]),
                "quantity": r["quantity"],
                "required_gender": r["required_gender"],
                "minimum_experience": r["minimum_experience"],
                "minimum_skill_level": r["minimum_skill_level"],
            })

        target_roles = [role] if role else list(req_by_role.keys())
        if not target_roles:
            return []

        selected_servers = await conn.fetch(
            "SELECT server_id FROM event_staff WHERE event_id = $1",
            event_id,
        )
        excluded_server_ids = {str(r["server_id"]) for r in selected_servers}

        query = """
            SELECT s.id, s.first_name, s.last_name, s.gender, c.name AS city,
                   s.years_experience,
                   CASE
                       WHEN sa.start_datetime <= $1 AND sa.end_datetime >= $2 AND sa.status = 'AVAILABLE'
                       THEN 'AVAILABLE'
                       ELSE 'UNAVAILABLE'
                   END AS availability_status
            FROM servers s
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= $1
                AND sa.end_datetime >= $2
            WHERE s.is_active = TRUE
        """
        params: list[Any] = [event_start, event_end]

        if search:
            params.append(f"%{search}%")
            query += f" AND (LOWER(s.first_name || ' ' || s.last_name) LIKE ${len(params)} OR LOWER(c.name) LIKE ${len(params)})"

        if excluded_server_ids:
            query += f" AND s.id NOT IN ({','.join(['$' + str(len(params) + i + 1) for i in range(len(excluded_server_ids))])})"
            for sid in excluded_server_ids:
                params.append(sid)

        rows = await conn.fetch(query, *params)

        all_server_ids = [str(r["id"]) for r in rows]
        skill_rows = await conn.fetch(
            """
            SELECT ss.server_id, s.name AS skill_name, ss.level
            FROM server_skills ss
            JOIN skills s ON ss.skill_id = s.id
            WHERE ss.server_id = ANY($1::uuid[])
            """,
            all_server_ids,
        )
        server_skills_map: dict[str, dict[str, int]] = {}
        for sk in skill_rows:
            sid = str(sk["server_id"])
            skill_name = normalize_text(sk["skill_name"].lower())
            server_skills_map.setdefault(sid, {})
            server_skills_map[sid][skill_name] = max(
                server_skills_map[sid].get(skill_name, 0), sk["level"]
            )

        result = []
        for r in rows:
            if r["availability_status"] != "AVAILABLE":
                continue

            server_id = str(r["id"])
            server_skills = server_skills_map.get(server_id, {})

            eligible = False
            matched_req = None
            matched_role = None
            for req_role in target_roles:
                role_reqs = req_by_role.get(req_role)
                if not role_reqs:
                    continue
                for req in role_reqs:
                    if req["required_gender"] and r["gender"] != req["required_gender"]:
                        continue
                    if (r["years_experience"] or 0) < req["minimum_experience"]:
                        continue
                    skill_level = server_skills.get(normalize_text(req_role.lower()), 0)
                    if skill_level < req["minimum_skill_level"]:
                        continue
                    eligible = True
                    matched_req = req
                    matched_role = req_role
                    break
                if eligible:
                    break

            if not eligible:
                continue

            result.append({
                "server_id": str(server_id),
                "server_name": f"{r['first_name']} {r['last_name']}".strip(),
                "gender": r["gender"],
                "city": r["city"],
                "years_experience": r["years_experience"] or 0,
                "skill_level": server_skills.get(normalize_text(matched_role.lower()), 0),
                "availability_status": r["availability_status"],
                "score": None,
                "distance_km": None,
                 "requirement_id": matched_req["id"] if matched_req else None,
                 "role": matched_role or (target_roles[0] if target_roles else ""),
             })

        return result


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"STAFFING", "CONFIRMED", "CANCELLED"},
    "STAFFING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"IN_PROGRESS", "COMPLETED", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
}


async def update_event_status(event_id: str, new_status: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            event_row = await conn.fetchrow(
                "SELECT id, status, name FROM events WHERE id = $1",
                event_id,
            )
            if not event_row:
                raise HTTPException(status_code=404, detail="Événement introuvable.")

            current_status = event_row["status"]
            if current_status == new_status:
                return {
                    "event_id": str(event_row["id"]),
                    "status": new_status,
                    "previous_status": current_status,
                    "message": f"L'événement est déjà dans le statut '{new_status}'.",
                }

            allowed = ALLOWED_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Transition de statut invalide: {current_status} → {new_status}.",
                )

            if new_status == "CONFIRMED":
                requirements = await conn.fetch(
                    """
                    SELECT id, role_name, quantity, required_gender,
                           minimum_experience, minimum_skill_level
                    FROM event_requirements
                    WHERE event_id = $1
                    """,
                    event_id,
                )
                if not requirements:
                    raise HTTPException(
                        status_code=400,
                        detail="Impossible de confirmer l'événement : aucun poste défini.",
                    )

                total_requested = sum(r["quantity"] for r in requirements)
                total_selected = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM event_staff
                    WHERE event_id = $1
                      AND assignment_status IN ('PROPOSED', 'CONFIRMED')
                    """,
                    event_id,
                )
                if total_selected < total_requested:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Impossible de confirmer l'événement : {total_requested - total_selected} poste(s) encore à pourvoir.",
                    )

            await conn.execute(
                "UPDATE events SET status = $1, updated_at = NOW() WHERE id = $2",
                new_status,
                event_id,
            )

            return {
                "event_id": str(event_row["id"]),
                "status": new_status,
                "previous_status": current_status,
                "message": f"Statut de l'événement mis à jour: {current_status} → {new_status}.",
            }


async def get_event_operations(event_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            """
            SELECT e.id, e.name, c.name AS city,
                   e.start_datetime, e.end_datetime, e.guest_count,
                   e.priority, e.is_urgent, e.status
            FROM events e
            JOIN cities c ON e.city_id = c.id
            WHERE e.id = $1
            LIMIT 1
            """,
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")

        event = serialize_row(dict(event_row))
        event_start = event["start_datetime"]
        event_end = event["end_datetime"]
        if isinstance(event_start, datetime):
            event_start = event_start.isoformat()
        if isinstance(event_end, datetime):
            event_end = event_end.isoformat()

        duration_minutes = None
        if event_start and event_end:
            try:
                start_dt = datetime.fromisoformat(event_start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(event_end.replace("Z", "+00:00"))
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            except Exception:
                duration_minutes = None

        requirements = await load_event_requirements_with_counts(event_id)
        assignments_raw = await load_event_staff_assignments(event_id)

        total_requested = sum(r["quantity"] for r in requirements)
        total_assigned = sum(r["selected"] or 0 for r in requirements)
        total_confirmed = sum(1 for a in assignments_raw if a["assignment_status"] == "CONFIRMED")
        total_missing = total_requested - total_assigned
        coverage_percentage = round((total_confirmed / total_requested) * 100, 1) if total_requested > 0 else 0.0

        requirements_summary = []
        for req in requirements:
            assigned = req["selected"] or 0
            confirmed = sum(1 for a in assignments_raw if a["role"] == req["role_name"] and a["assignment_status"] == "CONFIRMED")
            missing = req["quantity"] - assigned
            if confirmed >= req["quantity"]:
                req_status = "COMPLETED"
            elif confirmed > 0:
                req_status = "PARTIEL"
            else:
                req_status = "CRITIQUE"
            requirements_summary.append({
                "requirement_id": str(req["id"]),
                "role_name": req["role_name"],
                "quantity": req["quantity"],
                "required_gender": req["required_gender"],
                "minimum_experience": req["minimum_experience"],
                "minimum_skill_level": req["minimum_skill_level"],
                "assigned": assigned,
                "confirmed": confirmed,
                "missing": missing,
                "status": req_status,
            })

        confirmed_staff = []
        for a in assignments_raw:
            if a["assignment_status"] == "CONFIRMED":
                confirmed_staff.append({
                    "assignment_id": str(a["id"]),
                    "server_id": str(a["server_id"]),
                    "server_name": f"{a['first_name']} {a['last_name']}".strip(),
                    "role": a["role"],
                    "assignment_status": a["assignment_status"],
                    "years_experience": a.get("years_experience"),
                    "skill_level": a.get("skill_level"),
                    "score": None,
                    "transport_status": None,
                })

        transport_groups_raw = await conn.fetch(
            """
            SELECT tg.id, tg.driver_server_id, tg.vehicle_id, tg.estimated_distance_km,
                   v.brand, v.model, v.seats_total,
                   s.first_name, s.last_name
            FROM transport_groups tg
            JOIN vehicles v ON tg.vehicle_id = v.id
            JOIN servers s ON tg.driver_server_id = s.id
            WHERE tg.event_id = $1
            ORDER BY tg.created_at ASC
            """,
            event_id,
        )

        transport_groups = []
        total_passengers = 0
        if transport_groups_raw:
            group_ids = [tg["id"] for tg in transport_groups_raw]
            passengers_raw = await conn.fetch(
                """
                SELECT tp.transport_group_id, tp.server_id, tp.pickup_order, tp.pickup_status,
                       s.first_name, s.last_name
                FROM transport_passengers tp
                JOIN servers s ON tp.server_id = s.id
                WHERE tp.transport_group_id = ANY($1::uuid[])
                ORDER BY tp.pickup_order ASC
                """,
                group_ids,
            )
            passengers_by_group: dict[str, list[dict[str, Any]]] = {}
            for p in passengers_raw:
                gid = str(p["transport_group_id"])
                passengers_by_group.setdefault(gid, []).append({
                    "server_id": str(p["server_id"]),
                    "name": f"{p['first_name']} {p['last_name']}".strip(),
                    "pickup_order": p["pickup_order"],
                    "pickup_status": p["pickup_status"],
                })
        else:
            passengers_by_group = {}

        for tg in transport_groups_raw:
            gid = str(tg["id"])
            passengers = passengers_by_group.get(gid, [])
            passenger_count = len(passengers)
            total_passengers += passenger_count
            transport_groups.append({
                "group_id": gid,
                "driver_name": f"{tg['first_name']} {tg['last_name']}".strip(),
                "vehicle": f"{tg['brand']} {tg['model']}",
                "capacity": tg["seats_total"],
                "passenger_count": passenger_count,
                "available_seats": max(0, tg["seats_total"] - passenger_count),
                "status": "CONFIRMED",
                "passengers": passengers,
            })

        unassigned_passengers = 0
        if total_confirmed > 0 and total_passengers > 0:
            assigned_server_ids = {s["server_id"] for s in confirmed_staff}
            for group in transport_groups:
                for passenger in group["passengers"]:
                    if passenger["server_id"] not in assigned_server_ids:
                        unassigned_passengers += 1

        alerts: list[dict[str, Any]] = []

        if event["status"] == "CANCELLED":
            alerts.append({
                "type": "event_status",
                "severity": "CRITICAL",
                "message": "Événement annulé.",
                "related_entity": str(event["id"]),
            })
        elif event["status"] == "COMPLETED":
            alerts.append({
                "type": "event_status",
                "severity": "INFO",
                "message": "Événement terminé.",
                "related_entity": str(event["id"]),
            })
        elif event["status"] == "IN_PROGRESS":
            alerts.append({
                "type": "event_status",
                "severity": "INFO",
                "message": "Événement en cours.",
                "related_entity": str(event["id"]),
            })
        elif event["status"] == "CONFIRMED":
            alerts.append({
                "type": "event_status",
                "severity": "INFO",
                "message": "Événement confirmé et prêt.",
                "related_entity": str(event["id"]),
            })

        if total_missing > 0:
            alerts.append({
                "type": "staffing",
                "severity": "WARNING",
                "message": f"{total_missing} poste(s) encore manquant(s).",
                "related_entity": str(event["id"]),
            })

        for req in requirements_summary:
            if req["status"] == "CRITIQUE":
                alerts.append({
                    "type": "critical_requirement",
                    "severity": "CRITICAL",
                    "message": f"{req['role_name']} : 0/{req['quantity']} confirmé(s).",
                    "related_entity": req["requirement_id"],
                })
            elif req["status"] == "PARTIEL":
                alerts.append({
                    "type": "partial_requirement",
                    "severity": "WARNING",
                    "message": f"{req['role_name']} : {req['confirmed']}/{req['quantity']} confirmé(s).",
                    "related_entity": req["requirement_id"],
                })

        if total_passengers > 0 and unassigned_passengers > 0:
            alerts.append({
                "type": "transport",
                "severity": "WARNING",
                "message": f"{unassigned_passengers} passager(s) sans affectation confirmée.",
                "related_entity": str(event["id"]),
            })

        if total_passengers > 0:
            alerts.append({
                "type": "transport",
                "severity": "INFO",
                "message": f"Transport confirmé pour {total_passengers} serveur(s).",
                "related_entity": str(event["id"]),
            })

        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

        attendance_rows = await conn.fetch(
            """
            SELECT ea.status, ea.check_in_at, ea.check_out_at
            FROM event_attendance ea
            WHERE ea.event_id = $1
            """,
            event_id,
        )
        attendance_summary = {
            "total_expected": len(attendance_rows),
            "present": sum(1 for r in attendance_rows if r["status"] == "PRESENT"),
            "late": sum(1 for r in attendance_rows if r["status"] == "LATE"),
            "absent": sum(1 for r in attendance_rows if r["status"] == "ABSENT"),
            "excused": sum(1 for r in attendance_rows if r["status"] == "EXCUSED"),
            "checked_out": sum(1 for r in attendance_rows if r["check_out_at"] is not None),
            "not_checked_in": sum(1 for r in attendance_rows if r["check_in_at"] is None and r["status"] in ("EXPECTED", "LATE", "ABSENT", "EXCUSED")),
        }
        attendance_rate = 0.0
        if attendance_summary["total_expected"] > 0:
            attendance_rate = round(((attendance_summary["present"] + attendance_summary["late"]) / attendance_summary["total_expected"]) * 100, 1)

        if attendance_summary["absent"] > 0:
            alerts.append({
                "type": "attendance",
                "severity": "CRITICAL",
                "message": f"{attendance_summary['absent']} serveur(s) absent(s).",
                "related_entity": str(event["id"]),
            })
        if attendance_summary["not_checked_in"] > 0 and event["status"] == "IN_PROGRESS":
            alerts.append({
                "type": "attendance",
                "severity": "WARNING",
                "message": f"{attendance_summary['not_checked_in']} serveur(s) non pointé(s).",
                "related_entity": str(event["id"]),
            })
        if attendance_rate >= 90:
            alerts.append({
                "type": "attendance",
                "severity": "INFO",
                "message": f"Taux de présence : {attendance_rate}%.",
                "related_entity": str(event["id"]),
            })

        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

        return {
            "event_id": str(event["id"]),
            "event_name": event["name"],
            "status": event["status"],
            "city": event["city"],
            "date": event_start.split("T")[0] if event_start and "T" in event_start else event_start,
            "guest_count": event["guest_count"],
            "duration_minutes": duration_minutes,
            "attendance_available": True,
            "attendance": {
                "summary": {
                    **attendance_summary,
                    "attendance_rate": attendance_rate,
                },
                "staff": [],
            },
            "staffing_summary": {
                "requested": total_requested,
                "assigned": total_assigned,
                "confirmed": total_confirmed,
                "missing": total_missing,
                "proposed": total_assigned - total_confirmed,
                "coverage_percentage": coverage_percentage,
            },
            "requirements": requirements_summary,
            "confirmed_staff": confirmed_staff,
            "transport": {
                "groups": transport_groups,
                "total_groups": len(transport_groups),
                "total_passengers": total_passengers,
                "unassigned_passengers": unassigned_passengers,
            },
            "alerts": alerts,
        }
