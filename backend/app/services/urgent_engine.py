import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import get_pool
from app.utils.datetime_utils import now_naive_utc
from app.services.selection_engine import (
    generate_staff_recommendations,
    haversine_km,
    load_event_requirements,
    load_server_skills,
    load_skill_names,
    load_servers_with_details,
    normalize_text,
    serialize_row,
)
from app.utils.selection_utils import compute_candidate_score
from app.utils.event_utils import load_event

URGENT_WAVE_SIZE = 5
URGENT_OFFER_EXPIRATION_MINUTES = 15


async def get_existing_offers(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, event_id, server_id, wave_number, status, sent_at, response_deadline
            FROM urgent_event_offers
            WHERE event_id = $1
            ORDER BY wave_number, sent_at
            """,
            event_id,
        )
        return [serialize_row(dict(r)) for r in rows]


async def get_confirmed_staff(event_id: str) -> set[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT server_id
            FROM event_staff
            WHERE event_id = $1
              AND assignment_status = 'CONFIRMED'
            """,
            event_id,
        )
        return {str(r["server_id"]) for r in rows}


async def generate_urgent_offers(event_id: str) -> dict[str, Any]:
    event = await load_event(event_id)
    if not event:
        return {"error": "Event not found", "status": "ERROR"}

    if not event.get("is_urgent"):
        return {"error": "URGENT_EVENT_REQUIRED", "status": "ERROR"}

    requirements = await load_event_requirements(event_id)
    existing_offers = await get_existing_offers(event_id)
    confirmed_staff = await get_confirmed_staff(event_id)

    max_wave = 0
    for offer in existing_offers:
        wave = offer.get("wave_number") or 0
        if wave > max_wave:
            max_wave = wave
    next_wave = max_wave + 1

    servers = await load_servers_with_details(event_id)
    server_ids = [s["server_id"] for s in servers]
    server_skills = await load_server_skills(server_ids)
    skill_names = await load_skill_names()

    event_start = datetime.fromisoformat(event["start_datetime"])
    event_end = datetime.fromisoformat(event["end_datetime"])

    excluded_servers: set[str] = set()
    for offer in existing_offers:
        sid = str(offer["server_id"])
        status = offer.get("status")
        wave = offer.get("wave_number") or 0
        if status == "ACCEPTED" or sid in confirmed_staff:
            excluded_servers.add(sid)
        elif status == "PENDING" and wave == next_wave - 1:
            excluded_servers.add(sid)
        elif status in ("DECLINED", "EXPIRED") and wave == next_wave - 1:
            pass
        elif status == "PENDING":
            excluded_servers.add(sid)

    remaining_requirements: list[dict[str, Any]] = []
    for req in requirements:
        role = req["role_name"]
        quantity = req["quantity"]
        accepted_count = 0
        for offer in existing_offers:
            if offer.get("status") == "ACCEPTED":
                sid = str(offer["server_id"])
                if sid in confirmed_staff:
                    accepted_count += 1
        remaining = max(0, quantity - accepted_count)
        if remaining > 0:
            remaining_requirements.append({**req, "remaining": remaining})

    if not remaining_requirements:
        return {
            "event_id": event_id,
            "status": "STAFFING_COMPLETE",
            "wave_number": next_wave,
            "offers_created": 0,
            "requirements": [],
            "offers": [],
        }

    recent_assignments = [s.get("recent_assignments") or 0 for s in servers]
    min_assignments = min(recent_assignments) if recent_assignments else 0
    max_assignments = max(recent_assignments) if recent_assignments else 1

    offers_created: list[dict[str, Any]] = []
    pool = await get_pool()
    async with pool.acquire() as conn:
        for req in remaining_requirements:
            req_id = str(req["id"])
            role_name = req["role_name"].lower()
            required_gender = req["required_gender"]
            min_exp = req["minimum_experience"]
            min_skill = req["minimum_skill_level"]
            remaining = req["remaining"]
            to_send = min(remaining, URGENT_WAVE_SIZE)

            eligible: list[dict[str, Any]] = []
            for server in servers:
                sid = server["server_id"]
                if sid in excluded_servers:
                    continue
                if not server.get("is_active"):
                    continue
                if server.get("availability_status") != "AVAILABLE":
                    continue
                if server.get("gender") != required_gender and required_gender is not None:
                    continue
                if (server.get("years_experience") or 0) < min_exp:
                    continue
                skills = server_skills.get(sid, [])
                has_skill = False
                max_level = 0
                for sk in skills:
                    sk_name = skill_names.get(str(sk["skill_id"]), "").lower()
                    if normalize_text(sk_name) == normalize_text(role_name):
                        has_skill = True
                        max_level = max(max_level, sk.get("level") or 0)
                if not has_skill:
                    continue
                if max_level < min_skill:
                    continue

                server_copy = dict(server)
                server_copy["main_skill_level"] = max_level
                score, _ = compute_candidate_score(
                    server_copy,
                    req,
                    event_start,
                    event_end,
                    settings.DEFAULT_EVENT_LATITUDE,
                    settings.DEFAULT_EVENT_LONGITUDE,
                    min_assignments,
                    max_assignments,
                )
                eligible.append({**server_copy, "score": score})

            eligible.sort(key=lambda x: x.get("score") or 0, reverse=True)
            selected = eligible[:to_send]

            for sel in selected:
                sid = sel["server_id"]
                excluded_servers.add(sid)
                deadline = now_naive_utc() + timedelta(minutes=URGENT_OFFER_EXPIRATION_MINUTES)
                row = await conn.fetchrow(
                    """
                    INSERT INTO urgent_event_offers (event_id, server_id, wave_number, response_deadline, status)
                    VALUES ($1, $2, $3, $4, 'PENDING')
                    RETURNING id, event_id, server_id, wave_number, status, sent_at, response_deadline
                    """,
                    event_id,
                    sid,
                    next_wave,
                    deadline,
                )
                offer_row = serialize_row(dict(row))
                server_name = f"{sel.get('first_name', '')} {sel.get('last_name', '')}".strip()
                offer_row["server_name"] = server_name
                offer_row["role"] = req["role_name"]
                offer_row["score"] = sel.get("score")
                offer_row["distance_km"] = None
                offer_row["reason"] = None
                offers_created.append(offer_row)

    return {
        "event_id": event_id,
        "status": "SUCCESS",
        "wave_number": next_wave,
        "offers_created": len(offers_created),
        "wave_size": len(offers_created),
        "offers_sent": len(offers_created),
        "pending_count": len(offers_created),
        "accepted_count": 0,
        "declined_count": 0,
        "expired_count": 0,
        "total_staff_needed": sum(r["quantity"] for r in remaining_requirements),
        "total_staff_confirmed": 0,
        "remaining_staff": sum(r["quantity"] for r in remaining_requirements),
        "can_generate_next_wave": False,
        "requirements": remaining_requirements,
        "offers": offers_created,
    }


async def accept_offer(event_id: str, offer_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        offer = await conn.fetchrow(
            """
            SELECT id, event_id, server_id, wave_number, status
            FROM urgent_event_offers
            WHERE id = $1 AND event_id = $2
            """,
            offer_id,
            event_id,
        )
        if not offer:
            return {"error": "Offer not found", "status": "ERROR"}
        if str(offer["event_id"]) != event_id:
            return {"error": "Offer does not belong to this event", "status": "ERROR"}
        if offer["status"] != "PENDING":
            return {"error": f"Offer is already {offer['status']}", "status": "ERROR"}

        existing_staff = await conn.fetchrow(
            """
            SELECT id FROM event_staff
            WHERE event_id = $1 AND server_id = $2
            """,
            event_id,
            offer["server_id"],
        )
        if existing_staff:
            return {"error": "Server already assigned to this event", "status": "ERROR"}

        async with conn.transaction():
            await conn.execute(
                "UPDATE urgent_event_offers SET status = 'ACCEPTED', responded_at = NOW() WHERE id = $1",
                offer_id,
            )
            staff_row = await conn.fetchrow(
                """
                INSERT INTO event_staff (event_id, server_id, role, assignment_status, assigned_at, confirmed_at)
                VALUES ($1, $2, $3, 'CONFIRMED', NOW(), NOW())
                RETURNING id, event_id, server_id, role, assignment_status, assigned_at, confirmed_at
                """,
                event_id,
                offer["server_id"],
                "Staff",
            )
            return {
                "status": "SUCCESS",
                "offer_id": str(offer["id"]),
                "event_staff": serialize_row(dict(staff_row)),
            }


async def decline_offer(event_id: str, offer_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        offer = await conn.fetchrow(
            """
            SELECT id, event_id, server_id, wave_number, status
            FROM urgent_event_offers
            WHERE id = $1 AND event_id = $2
            """,
            offer_id,
            event_id,
        )
        if not offer:
            return {"error": "Offer not found", "status": "ERROR"}
        if str(offer["event_id"]) != event_id:
            return {"error": "Offer does not belong to this event", "status": "ERROR"}
        if offer["status"] != "PENDING":
            return {"error": f"Offer is already {offer['status']}", "status": "ERROR"}

        await conn.execute(
            "UPDATE urgent_event_offers SET status = 'DECLINED', responded_at = NOW() WHERE id = $1",
            offer_id,
        )
        return {"status": "SUCCESS", "offer_id": str(offer["id"])}


async def expire_offer(event_id: str, offer_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        offer = await conn.fetchrow(
            """
            SELECT id, event_id, server_id, wave_number, status
            FROM urgent_event_offers
            WHERE id = $1 AND event_id = $2
            """,
            offer_id,
            event_id,
        )
        if not offer:
            return {"error": "Offer not found", "status": "ERROR"}
        if str(offer["event_id"]) != event_id:
            return {"error": "Offer does not belong to this event", "status": "ERROR"}
        if offer["status"] != "PENDING":
            return {"error": f"Offer is already {offer['status']}", "status": "ERROR"}

        await conn.execute(
            "UPDATE urgent_event_offers SET status = 'EXPIRED', responded_at = NOW() WHERE id = $1",
            offer_id,
        )
        return {"status": "SUCCESS", "offer_id": str(offer["id"])}


async def get_urgent_status(event_id: str) -> dict[str, Any]:
    event = await load_event(event_id)
    if not event:
        return {"error": "Event not found", "status": "ERROR"}

    requirements = await load_event_requirements(event_id)
    offers = await get_existing_offers(event_id)
    confirmed_staff = await get_confirmed_staff(event_id)

    server_ids = [str(o["server_id"]) for o in offers]
    servers = await load_servers_with_details(event_id)
    server_map = {str(s["server_id"]): s for s in servers}
    server_skills = await load_server_skills(server_ids) if server_ids else {}
    skill_names = await load_skill_names()

    requirements_status: list[dict[str, Any]] = []
    total_required = 0
    total_confirmed = 0
    for req in requirements:
        role = req["role_name"]
        quantity = req["quantity"]
        accepted = 0
        for offer in offers:
            if offer.get("status") == "ACCEPTED" and str(offer["server_id"]) in confirmed_staff:
                accepted += 1
        remaining = max(0, quantity - accepted)
        total_required += quantity
        total_confirmed += accepted
        requirements_status.append({
            "role": role,
            "requested": quantity,
            "accepted": accepted,
            "remaining": remaining,
        })

    waves: list[dict[str, Any]] = []
    current_wave_number = 0
    current_wave_offers_sent = 0
    current_wave_pending = 0
    current_wave_accepted = 0
    current_wave_declined = 0
    current_wave_expired = 0
    if offers:
        wave_numbers = sorted({o.get("wave_number") or 0 for o in offers})
        current_wave_number = wave_numbers[-1]
        for wave_num in wave_numbers:
            wave_offers = [o for o in offers if (o.get("wave_number") or 0) == wave_num]
            wave_stats = {
                "wave_number": wave_num,
                "offers_sent": len(wave_offers),
                "pending": sum(1 for o in wave_offers if o.get("status") == "PENDING"),
                "accepted": sum(1 for o in wave_offers if o.get("status") == "ACCEPTED"),
                "declined": sum(1 for o in wave_offers if o.get("status") == "DECLINED"),
                "expired": sum(1 for o in wave_offers if o.get("status") == "EXPIRED"),
            }
            waves.append(wave_stats)
            if wave_num == current_wave_number:
                current_wave_offers_sent = wave_stats["offers_sent"]
                current_wave_pending = wave_stats["pending"]
                current_wave_accepted = wave_stats["accepted"]
                current_wave_declined = wave_stats["declined"]
                current_wave_expired = wave_stats["expired"]

    enriched_offers = []
    for o in offers:
        sid = str(o["server_id"])
        server = server_map.get(sid, {})
        server_name = f"{server.get('first_name', '')} {server.get('last_name', '')}".strip() or sid
        role = "Staff"
        if o.get("status") == "ACCEPTED" and sid in confirmed_staff:
            role = "Staff"
        else:
            skills = server_skills.get(sid, [])
            for sk in skills:
                sk_name = skill_names.get(str(sk["skill_id"]), "").lower()
                for req in requirements:
                    if normalize_text(sk_name) == normalize_text(req["role_name"].lower()):
                        role = req["role_name"]
                        break
                else:
                    continue
                break
        score = None
        distance_km = None
        reason = None
        if o.get("status") == "ACCEPTED":
            score = server.get("score")
            if server.get("current_latitude") and server.get("current_longitude"):
                event_lat = event.get("event_latitude", settings.DEFAULT_EVENT_LATITUDE)
                event_lon = event.get("event_longitude", settings.DEFAULT_EVENT_LONGITUDE)
                distance_km = haversine_km(
                    float(server["current_latitude"]),
                    float(server["current_longitude"]),
                    event_lat,
                    event_lon,
                )
        enriched_offers.append({
            "offer_id": str(o["id"]),
            "server_id": sid,
            "server_name": server_name,
            "role": role,
            "status": o.get("status", "PENDING"),
            "wave_number": o.get("wave_number") or 0,
            "created_at": o.get("sent_at"),
            "expires_at": o.get("response_deadline"),
            "score": score,
            "distance_km": distance_km,
            "reason": reason,
        })

    can_generate_next_wave = event.get("is_urgent") and (
        not offers or current_wave_pending == 0
    )

    return {
        "event_id": str(event["id"]),
        "is_urgent": event["is_urgent"],
        "event": {
            "id": event["id"],
            "name": event["name"],
            "is_urgent": event["is_urgent"],
            "status": event["status"],
        },
        "requirements": requirements_status,
        "waves": waves,
        "staffing": {
            "total_required": total_required,
            "total_confirmed": total_confirmed,
            "total_remaining": total_required - total_confirmed,
        },
        "wave_number": current_wave_number,
        "wave_size": current_wave_offers_sent,
        "offers_sent": current_wave_offers_sent,
        "pending_count": current_wave_pending,
        "accepted_count": current_wave_accepted,
        "declined_count": current_wave_declined,
        "expired_count": current_wave_expired,
        "total_staff_needed": total_required,
        "total_staff_confirmed": total_confirmed,
        "remaining_staff": total_required - total_confirmed,
        "can_generate_next_wave": can_generate_next_wave,
        "offers": enriched_offers,
    }

