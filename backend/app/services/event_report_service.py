from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool
from app.services.event_service import get_event_operations
from app.services.gamification_engine import (
    load_evaluations,
    load_server_names,
)


async def get_event_report(event_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT id, status FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")

        event_status = event_row["status"]

        if event_status == "CANCELLED":
            return {
                "event_id": event_id,
                "event_name": "",
                "status": "CANCELLED",
                "is_final": False,
                "event": {},
                "staffing": {},
                "requirements": [],
                "attendance": {"available": False},
                "staff": [],
                "transport": {
                    "total_groups": 0,
                    "confirmed_groups": 0,
                    "total_passengers": 0,
                    "assigned_passengers": 0,
                    "unassigned_passengers": 0,
                },
                "gamification": {
                    "completion_points": 0,
                    "performance_points": 0,
                    "total_points": 0,
                },
                "final_kpis": {
                    "staffing_rate": 0.0,
                    "attendance_rate": 0.0,
                    "requirement_fulfillment_rate": 0.0,
                    "transport_coverage_rate": 0.0,
                },
                "alerts": [
                    {
                        "type": "event_status",
                        "severity": "CRITICAL",
                        "message": "Événement annulé. Aucun rapport final disponible.",
                        "related_entity": event_id,
                    }
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        if event_status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail="Le rapport final est disponible uniquement pour les événements terminés.",
            )

    operations = await get_event_operations(event_id)

    event_name = operations.get("event_name", "")
    city = operations.get("city", "")
    date = operations.get("date", "")
    guest_count = operations.get("guest_count", 0)
    duration_minutes = operations.get("duration_minutes")

    staffing_summary = operations.get("staffing_summary", {})
    requirements_summary = operations.get("requirements", [])
    attendance_data = operations.get("attendance", {})
    attendance_summary = attendance_data.get("summary", {}) if isinstance(attendance_data, dict) else {}
    transport_data = operations.get("transport", {})
    alerts = operations.get("alerts", [])

    total_requested = staffing_summary.get("requested", 0)
    total_confirmed = staffing_summary.get("confirmed", 0)
    total_missing = staffing_summary.get("missing", 0)
    coverage_percentage = staffing_summary.get("coverage_percentage", 0.0)

    requirements: list[dict[str, Any]] = []
    for req in requirements_summary:
        requirements.append({
            "requirement_id": str(req.get("requirement_id", "")),
            "role": req.get("role_name", ""),
            "requested": req.get("quantity", 0),
            "assigned": req.get("assigned", 0),
            "confirmed": req.get("confirmed", 0),
            "fulfilled": req.get("confirmed", 0) >= req.get("quantity", 0),
            "status": req.get("status", "CRITIQUE"),
        })

    attendance_available = operations.get("attendance_available", False)
    total_expected = attendance_summary.get("total_expected", 0)
    present = attendance_summary.get("present", 0)
    late = attendance_summary.get("late", 0)
    absent = attendance_summary.get("absent", 0)
    attendance_rate = attendance_summary.get("attendance_rate", 0.0)

    transport_groups = transport_data.get("groups", [])
    total_groups = transport_data.get("total_groups", 0)
    total_passengers = transport_data.get("total_passengers", 0)
    unassigned_passengers = transport_data.get("unassigned_passengers", 0)
    assigned_passengers = total_passengers - unassigned_passengers
    confirmed_groups = sum(1 for g in transport_groups if g.get("status") == "CONFIRMED")

    confirmed_staff_raw = operations.get("confirmed_staff", [])
    server_ids = [str(s.get("server_id", "")) for s in confirmed_staff_raw if s.get("server_id")]
    server_names = {}
    if server_ids:
        server_names = await load_server_names(server_ids)

    evaluations = await load_evaluations(event_id)

    async with pool.acquire() as conn:
        point_transactions = await conn.fetch(
            """
            SELECT pt.server_id, pt.points, pt.transaction_type, pt.reason
            FROM point_transactions pt
            WHERE pt.event_id = $1
            """,
            event_id,
        )

    points_by_server: dict[str, dict[str, int]] = {}
    for tx in point_transactions:
        sid = str(tx["server_id"])
        if sid not in points_by_server:
            points_by_server[sid] = {"completion_points": 0, "performance_points": 0, "total_points": 0}
        points_by_server[sid]["total_points"] += tx["points"]
        reason = tx["reason"] or ""
        if reason.startswith("Completion:"):
            points_by_server[sid]["completion_points"] += tx["points"]
        elif reason.startswith("Performance:"):
            points_by_server[sid]["performance_points"] += tx["points"]

    staff_report: list[dict[str, Any]] = []
    for assignment in confirmed_staff_raw:
        sid = str(assignment.get("server_id", ""))
        name = assignment.get("server_name", "") or server_names.get(sid, "Inconnu")
        role = assignment.get("role", "")
        assignment_status = assignment.get("assignment_status", "")

        attendance_status = None
        check_in_at = None
        check_out_at = None
        if attendance_available and isinstance(attendance_data, dict):
            for staff_att in attendance_data.get("staff", []):
                if str(staff_att.get("server_id", "")) == sid:
                    attendance_status = staff_att.get("status")
                    check_in_at = staff_att.get("check_in_at")
                    check_out_at = staff_att.get("check_out_at")
                    break

        evaluation = evaluations.get(sid)
        evaluation_score = None
        evaluation_comment = None
        evaluated = False
        if evaluation:
            evaluated = True
            evaluation_score = round((
                evaluation["punctuality"]
                + evaluation["work_quality"]
                + evaluation["presentation"]
                + evaluation["teamwork"]
                + evaluation["client_relation"]
            ) / 5.0, 1)
            evaluation_comment = evaluation.get("comment")

        pts = points_by_server.get(sid, {"completion_points": 0, "performance_points": 0, "total_points": 0})

        staff_report.append({
            "server_id": sid,
            "name": name,
            "role": role,
            "assignment_status": assignment_status,
            "attendance_status": attendance_status,
            "check_in_at": check_in_at,
            "check_out_at": check_out_at,
            "completion_points": pts.get("completion_points", 0),
            "performance_points": pts.get("performance_points", 0),
            "total_points": pts.get("total_points", 0),
            "evaluation_score": evaluation_score,
            "evaluation_comment": evaluation_comment,
            "evaluated": evaluated,
        })

    total_completion_points = sum(s.get("completion_points", 0) for s in staff_report)
    total_performance_points = sum(s.get("performance_points", 0) for s in staff_report)
    total_points = total_completion_points + total_performance_points

    staffing_rate = round((total_confirmed / total_requested) * 100, 1) if total_requested > 0 else 0.0
    requirement_fulfillment_rate = round((sum(1 for r in requirements if r["fulfilled"]) / len(requirements)) * 100, 1) if requirements else 0.0
    transport_coverage_rate = round((assigned_passengers / total_passengers) * 100, 1) if total_passengers > 0 else 0.0

    total_evaluated = 0
    evaluation_scores: list[float] = []
    for s in staff_report:
        if s.get("evaluated"):
            total_evaluated += 1
            score = s.get("evaluation_score")
            if score is not None:
                evaluation_scores.append(score)

    evaluation_coverage = round((total_evaluated / total_confirmed) * 100, 1) if total_confirmed > 0 else 0.0
    average_score = round(sum(evaluation_scores) / len(evaluation_scores), 1) if evaluation_scores else None
    highest_score = max(evaluation_scores) if evaluation_scores else None
    lowest_score = min(evaluation_scores) if evaluation_scores else None

    excellent_count = sum(1 for s in evaluation_scores if s >= 9)
    good_count = sum(1 for s in evaluation_scores if 7 <= s < 9)
    average_count = sum(1 for s in evaluation_scores if 5 <= s < 7)
    needs_improvement_count = sum(1 for s in evaluation_scores if s < 5)

    evaluation_summary = {
        "total_evaluated": total_evaluated,
        "total_confirmed": total_confirmed,
        "evaluation_coverage": evaluation_coverage,
        "average_score": average_score,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "excellent_count": excellent_count,
        "good_count": good_count,
        "average_count": average_count,
        "needs_improvement_count": needs_improvement_count,
    }

    final_kpis = {
        "staffing_rate": staffing_rate,
        "attendance_rate": attendance_rate,
        "requirement_fulfillment_rate": requirement_fulfillment_rate,
        "transport_coverage_rate": transport_coverage_rate,
        "evaluation_coverage": evaluation_coverage,
    }

    for req in requirements:
        if not req["fulfilled"]:
            alerts.append({
                "type": "requirement",
                "severity": "CRITICAL",
                "message": f"{req['role']} : {req['confirmed']}/{req['requested']} poste(s) non pourvu(s).",
                "related_entity": req["requirement_id"],
            })
        elif req.get("status") == "PARTIEL":
            alerts.append({
                "type": "requirement",
                "severity": "WARNING",
                "message": f"{req['role']} : {req['confirmed']}/{req['requested']} confirmé(s).",
                "related_entity": req["requirement_id"],
            })

    if absent > 0:
        alerts.append({
            "type": "attendance",
            "severity": "CRITICAL",
            "message": f"{absent} serveur(s) absent(s) lors de l'événement.",
            "related_entity": event_id,
        })
    if late > 0:
        alerts.append({
            "type": "attendance",
            "severity": "WARNING",
            "message": f"{late} serveur(s) en retard.",
            "related_entity": event_id,
        })

    if not attendance_available:
        alerts.append({
            "type": "attendance",
            "severity": "WARNING",
            "message": "Données de présence indisponibles.",
            "related_entity": event_id,
        })

    if total_missing > 0:
        alerts.append({
            "type": "staffing",
            "severity": "WARNING",
            "message": f"{total_missing} poste(s) manquant(s) à la fin de l'événement.",
            "related_entity": event_id,
        })

    if total_passengers > 0 and unassigned_passengers > 0:
        alerts.append({
            "type": "transport",
            "severity": "WARNING",
            "message": f"{unassigned_passengers} passager(s) sans transport assigné.",
            "related_entity": event_id,
        })

    alerts.append({
        "type": "event_status",
        "severity": "INFO",
        "message": "Événement terminé. Rapport final généré.",
        "related_entity": event_id,
    })

    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: severity_order.get(a.get("severity", ""), 3))

    return {
        "event_id": event_id,
        "event_name": event_name,
        "status": event_status,
        "is_final": True,
        "event": {
            "name": event_name,
            "city": city,
            "date": date,
            "guest_count": guest_count,
            "duration_minutes": duration_minutes,
        },
        "staffing": {
            "requested": total_requested,
            "assigned": staffing_summary.get("assigned", 0),
            "confirmed": total_confirmed,
            "completed": total_confirmed,
            "missing": total_missing,
            "coverage_percentage": coverage_percentage,
        },
        "requirements": requirements,
        "attendance": {
            "available": attendance_available,
            "expected": total_expected,
            "present": present,
            "late": late,
            "absent": absent,
            "attendance_rate": attendance_rate,
        },
        "staff": staff_report,
        "transport": {
            "total_groups": total_groups,
            "confirmed_groups": confirmed_groups,
            "total_passengers": total_passengers,
            "assigned_passengers": assigned_passengers,
            "unassigned_passengers": unassigned_passengers,
        },
        "gamification": {
            "completion_points": total_completion_points,
            "performance_points": total_performance_points,
            "total_points": total_points,
        },
        "evaluation_summary": evaluation_summary,
        "final_kpis": final_kpis,
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
