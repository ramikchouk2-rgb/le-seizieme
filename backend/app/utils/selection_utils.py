import math
from datetime import datetime
from typing import Any

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
    import unicodedata
    normalized = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: serialize_value(v) for k, v in row.items()}


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 100.0
    return max(0.0, min(100.0, ((value - min_val) / (max_val - min_val)) * 100.0))


SCORING_WEIGHTS = {
    "skill_match": 0.25,
    "performance": 0.20,
    "experience": 0.15,
    "availability": 0.15,
    "distance": 0.10,
    "punctuality_discipline": 0.05,
    "teamwork": 0.05,
    "workload": 0.05,
}


def compute_candidate_score(
    candidate: dict[str, Any],
    requirement: dict[str, Any],
    event_start: datetime,
    event_end: datetime,
    event_lat: float,
    event_lon: float,
    min_assignments: int,
    max_assignments: int,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    scores: dict[str, float] = {}

    skill_level = candidate.get("main_skill_level") or 0
    required_level = requirement.get("minimum_skill_level", 1)
    skill_match = normalize_score(skill_level, required_level, 10)
    scores["skill_match"] = skill_match
    if skill_level >= required_level:
        reasons.append(f"Skill level {skill_level}/10 meets requirement {required_level}")

    speed = candidate.get("speed_score") or 0
    punctuality = candidate.get("punctuality_score") or 0
    presentation = candidate.get("presentation_score") or 0
    communication = candidate.get("communication_score") or 0
    performance = (speed + punctuality + presentation + communication) / 4.0
    scores["performance"] = normalize_score(performance, 1, 10)
    if performance >= 7:
        reasons.append("Strong performance profile")

    experience = candidate.get("years_experience") or 0
    min_exp = requirement.get("minimum_experience", 0)
    scores["experience"] = normalize_score(experience, min_exp, 15)
    if experience >= min_exp:
        reasons.append(f"{experience} years experience")

    availability = candidate.get("availability_status")
    if availability == "AVAILABLE":
        scores["availability"] = 100.0
        reasons.append("Available for entire event")
    else:
        scores["availability"] = 0.0

    lat = candidate.get("current_latitude")
    lon = candidate.get("current_longitude")
    distance = None
    if lat is not None and lon is not None:
        distance = haversine_km(event_lat, event_lon, float(lat), float(lon))
        if distance <= 20:
            scores["distance"] = 100.0
            reasons.append(f"{distance} km from event")
        elif distance <= 50:
            scores["distance"] = 70.0
            reasons.append(f"{distance} km from event")
        else:
            scores["distance"] = 40.0
            reasons.append(f"{distance} km from event")
        candidate["distance_km"] = distance
    else:
        scores["distance"] = 50.0
        candidate["distance_km"] = None

    discipline = candidate.get("discipline_score") or 0
    scores["punctuality_discipline"] = normalize_score(discipline, 1, 10)
    if discipline >= 7:
        reasons.append("Strong punctuality/discipline")

    teamwork = candidate.get("teamwork_score") or 0
    scores["teamwork"] = normalize_score(teamwork, 1, 10)
    if teamwork >= 7:
        reasons.append("Strong teamwork")

    recent = candidate.get("recent_assignments") or 0
    if max_assignments > min_assignments:
        workload_ratio = (recent - min_assignments) / (max_assignments - min_assignments)
        workload_score = 100.0 - (workload_ratio * 30.0)
    else:
        workload_score = 100.0
    scores["workload"] = max(0.0, min(100.0, workload_score))
    if recent <= min_assignments:
        reasons.append("Low recent workload")

    total = (
        scores["skill_match"] * SCORING_WEIGHTS["skill_match"]
        + scores["performance"] * SCORING_WEIGHTS["performance"]
        + scores["experience"] * SCORING_WEIGHTS["experience"]
        + scores["availability"] * SCORING_WEIGHTS["availability"]
        + scores["distance"] * SCORING_WEIGHTS["distance"]
        + scores["punctuality_discipline"] * SCORING_WEIGHTS["punctuality_discipline"]
        + scores["teamwork"] * SCORING_WEIGHTS["teamwork"]
        + scores["workload"] * SCORING_WEIGHTS["workload"]
    )
    candidate["score"] = round(total, 1)
    candidate["reasons"] = reasons
    return total, reasons
