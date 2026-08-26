import math
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import get_pool


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (uuid.UUID,)):
        return str(value)
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize(v) for k, v in row.items()}


from app.utils.event_utils import load_event


async def load_event_requirements(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, event_id, role_name, quantity, required_gender,
                   minimum_experience, minimum_skill_level, notes
            FROM event_requirements
            WHERE event_id = $1
            ORDER BY role_name, required_gender
            """,
            event_id,
        )
        return [serialize_row(dict(r)) for r in rows]


async def load_skill_map() -> dict[str, str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM skills")
        return {r["name"].lower(): str(r["id"]) for r in rows}


async def load_servers_with_details(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                s.id AS server_id,
                s.first_name,
                s.last_name,
                s.gender,
                s.years_experience,
                s.is_active,
                c.name AS city_name,
                sl.latitude AS current_latitude,
                sl.longitude AS current_longitude,
                sp.speed_score,
                sp.punctuality_score,
                sp.presentation_score,
                sp.communication_score,
                sp.teamwork_score,
                sp.discipline_score,
                sp.endurance_score,
                sp.worker_type,
                sa.status AS availability_status,
                sa.start_datetime AS availability_start,
                sa.end_datetime AS availability_end,
                ev.recent_assignments
            FROM servers s
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
            LEFT JOIN server_profile sp ON s.id = sp.server_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS recent_assignments
                FROM event_staff es
                WHERE es.server_id = s.id
                  AND es.assigned_at >= NOW() - INTERVAL '30 days'
            ) ev ON TRUE
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= $1
                AND sa.end_datetime >= $1
            WHERE s.is_active = TRUE
            """,
            datetime.now(timezone.utc).replace(tzinfo=None),
        )
        return [serialize_row(dict(r)) for r in rows]


async def load_server_skills(server_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT server_id, skill_id, level, years_experience
            FROM server_skills
            WHERE server_id = ANY($1::uuid[])
            """,
            server_ids,
        )
        skills: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            skills.setdefault(str(r["server_id"]), []).append(serialize_row(dict(r)))
        return skills


async def load_skill_names() -> dict[str, str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM skills")
        return {str(r["id"]): r["name"] for r in rows}


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 100.0
    return max(0.0, min(100.0, ((value - min_val) / (max_val - min_val)) * 100.0))


from app.utils.selection_utils import compute_candidate_score


async def generate_staff_recommendations(event_id: str) -> dict[str, Any]:
    event = await load_event(event_id)
    if not event:
        return {"error": "Event not found", "status": "ERROR"}

    requirements = await load_event_requirements(event_id)
    skill_map = await load_skill_map()
    servers = await load_servers_with_details(event_id)
    server_ids = [s["server_id"] for s in servers]
    server_skills = await load_server_skills(server_ids)
    skill_names = await load_skill_names()

    event_start_raw = event["start_datetime"]
    event_end_raw = event["end_datetime"]
    event_lat = float(event.get("event_latitude") or settings.DEFAULT_EVENT_LATITUDE)
    event_lon = float(event.get("event_longitude") or settings.DEFAULT_EVENT_LONGITUDE)

    event_start = event_start_raw.isoformat() if isinstance(event_start_raw, datetime) else event_start_raw
    event_end = event_end_raw.isoformat() if isinstance(event_end_raw, datetime) else event_end_raw

    event = {
        "event_id": str(event["id"]),
        "name": event["name"],
        "city": event.get("city_name", ""),
        "start_datetime": event_start,
        "end_datetime": event_end,
        "guest_count": event["guest_count"],
        "alcohol_service": event["alcohol_service"],
        "food_products_count": event["food_products_count"],
        "requirements": [
            {
                "requirement_id": str(r["id"]),
                "role_name": r["role_name"],
                "quantity": r["quantity"],
                "required_gender": r["required_gender"],
                "minimum_experience": r["minimum_experience"],
                "minimum_skill_level": r["minimum_skill_level"],
            }
            for r in requirements
        ],
    }

    recent_assignments = [s.get("recent_assignments") or 0 for s in servers]
    min_assignments = min(recent_assignments) if recent_assignments else 0
    max_assignments = max(recent_assignments) if recent_assignments else 1

    def _requirement_difficulty(req: dict[str, Any]) -> tuple[int, int, int]:
        gender_penalty = 0 if req.get("required_gender") is None else 1000
        eligible_count = 0
        for server in servers:
            if not server.get("is_active"):
                continue
            if server.get("availability_status") != "AVAILABLE":
                continue
            if server.get("gender") != req.get("required_gender") and req.get("required_gender") is not None:
                continue
            if (server.get("years_experience") or 0) < req.get("minimum_experience", 0):
                continue
            sid = server["server_id"]
            skills = server_skills.get(sid, [])
            has_skill = False
            max_level = 0
            for sk in skills:
                sk_name = skill_names.get(str(sk["skill_id"]), "").lower()
                if normalize_text(sk_name) == normalize_text(req["role_name"].lower()):
                    has_skill = True
                    max_level = max(max_level, sk.get("level") or 0)
            if has_skill and max_level >= req.get("minimum_skill_level", 1):
                eligible_count += 1
        return (
            -eligible_count,
            req.get("minimum_skill_level", 0),
            req.get("minimum_experience", 0),
            gender_penalty,
        )

    requirements_sorted = sorted(requirements, key=_requirement_difficulty, reverse=True)

    global_selected: set[str] = set()
    assignments: dict[str, set[str]] = {str(r["id"]): set() for r in requirements_sorted}
    all_excluded: list[dict[str, Any]] = []
    requirement_results: list[dict[str, Any]] = []

    for req in requirements_sorted:
        req_id = str(req["id"])
        role_name = req["role_name"].lower()
        required_gender = req["required_gender"]
        min_exp = req["minimum_experience"]
        min_skill = req["minimum_skill_level"]
        quantity = req["quantity"]

        eligible: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []

        for server in servers:
            sid = server["server_id"]
            if sid in global_selected:
                continue
            if sid in assignments[req_id]:
                continue

            if not server.get("is_active"):
                excluded.append({**server, "exclusion_reason": "Server inactive"})
                continue

            if server.get("availability_status") != "AVAILABLE":
                excluded.append({**server, "exclusion_reason": f"Unavailable during event: {server.get('availability_status')}"})
                continue

            if server.get("gender") != required_gender and required_gender is not None:
                excluded.append({**server, "exclusion_reason": f"Gender mismatch: required {required_gender}"})
                continue

            if (server.get("years_experience") or 0) < min_exp:
                excluded.append({**server, "exclusion_reason": f"Insufficient experience: {server.get('years_experience')} < {min_exp}"})
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
                excluded.append({**server, "exclusion_reason": f"Missing required skill: {req['role_name']}"})
                continue
            if max_level < min_skill:
                excluded.append({**server, "exclusion_reason": f"Insufficient skill level: {max_level} < {min_skill}"})
                continue

            server_copy = dict(server)
            server_copy["main_skill_level"] = max_level
            server_copy["name"] = f"{server_copy.get('first_name', '')} {server_copy.get('last_name', '')}".strip()
            server_copy["city"] = server_copy.pop("city_name", "")
            server_copy["experience_years"] = server_copy.pop("years_experience", 0)
            server_copy["role"] = req["role_name"]
            score, reasons = compute_candidate_score(
                server_copy,
                req,
                event_start,
                event_end,
                event_lat,
                event_lon,
                min_assignments,
                max_assignments,
            )
            server_copy["score"] = score
            server_copy["reasons"] = reasons
            eligible.append(server_copy)

        eligible.sort(key=lambda x: x.get("score") or 0, reverse=True)
        selected = eligible[:quantity]

        for sel in selected:
            global_selected.add(sel["server_id"])
            assignments[req_id].add(sel["server_id"])

        requirement_results.append({
            "requirement": {
                "requirement_id": req_id,
                "role_name": req["role_name"],
                "quantity": req["quantity"],
                "required_gender": req["required_gender"],
                "minimum_experience": req["minimum_experience"],
                "minimum_skill_level": req["minimum_skill_level"],
            },
            "candidates": eligible,
            "selected": selected,
            "status": "FILLED" if len(selected) >= quantity else "INSUFFICIENT_STAFF",
            "message": None if len(selected) >= quantity else f"Only {len(selected)}/{quantity} eligible candidates found",
        })
        all_excluded.extend(excluded)

    total_eligible = sum(len(r["candidates"]) for r in requirement_results)
    total_selected = sum(len(r["selected"]) for r in requirement_results)
    total_excluded = len(all_excluded)

    return {
        "event": event,
        "requirements": requirement_results,
        "total_eligible": total_eligible,
        "total_excluded": total_excluded,
        "total_selected": total_selected,
        "status": "SUCCESS",
    }
