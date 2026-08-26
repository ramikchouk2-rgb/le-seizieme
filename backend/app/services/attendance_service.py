from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.database import get_pool


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "EXPECTED": {"PRESENT", "LATE", "ABSENT", "EXCUSED", "LEFT"},
    "PRESENT": {"LEFT"},
    "LATE": {"LEFT"},
    "ABSENT": set(),
    "EXCUSED": set(),
    "LEFT": set(),
}


async def get_event_attendance(event_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        event_row = await conn.fetchrow(
            "SELECT id FROM events WHERE id = $1",
            event_id,
        )
        if not event_row:
            raise HTTPException(status_code=404, detail="Événement introuvable.")

        rows = await conn.fetch(
            """
            SELECT ea.id, ea.event_id, ea.event_staff_id, ea.status, ea.check_in_at, ea.check_out_at, ea.note,
                   es.server_id, s.first_name, s.last_name, es.role
            FROM event_attendance ea
            JOIN event_staff es ON ea.event_staff_id = es.id
            JOIN servers s ON es.server_id = s.id
            WHERE ea.event_id = $1
            ORDER BY es.assigned_at ASC
            """,
            event_id,
        )

        staff = []
        summary = {
            "total_expected": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "excused": 0,
            "checked_out": 0,
            "not_checked_in": 0,
        }

        for r in rows:
            staff.append({
                "id": str(r["id"]),
                "event_id": str(r["event_id"]),
                "event_staff_id": str(r["event_staff_id"]),
                "server_id": str(r["server_id"]),
                "server_name": f"{r['first_name']} {r['last_name']}".strip(),
                "role": r["role"],
                "status": r["status"],
                "check_in_at": r["check_in_at"].isoformat() if isinstance(r["check_in_at"], datetime) else (r["check_in_at"] if r["check_in_at"] else None),
                "check_out_at": r["check_out_at"].isoformat() if isinstance(r["check_out_at"], datetime) else (r["check_out_at"] if r["check_out_at"] else None),
                "note": r["note"],
            })
            summary[r["status"].lower()] = summary.get(r["status"].lower(), 0) + 1
            summary["total_expected"] += 1
            if r["check_out_at"]:
                summary["checked_out"] += 1
            if not r["check_in_at"] and r["status"] in ("EXPECTED", "LATE", "ABSENT", "EXCUSED"):
                summary["not_checked_in"] += 1

        attendance_rate = 0.0
        if summary["total_expected"] > 0:
            attendance_rate = round(((summary["present"] + summary["late"]) / summary["total_expected"]) * 100, 1)

        return {
            "event_id": event_id,
            "summary": summary,
            "staff": staff,
            "attendance_rate": attendance_rate,
        }


async def initialize_event_attendance(event_id: str) -> dict[str, Any]:
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
                    detail="Impossible d'initialiser les présences pour cet événement.",
                )

            staff_rows = await conn.fetch(
                """
                SELECT es.id
                FROM event_staff es
                WHERE es.event_id = $1
                  AND es.assignment_status IN ('CONFIRMED', 'PROPOSED')
                """,
                event_id,
            )

            initialized = 0
            for staff_row in staff_rows:
                existing = await conn.fetchrow(
                    "SELECT id FROM event_attendance WHERE event_staff_id = $1",
                    staff_row["id"],
                )
                if not existing:
                    await conn.execute(
                        """
                        INSERT INTO event_attendance (event_id, event_staff_id, status)
                        VALUES ($1, $2, 'EXPECTED')
                        """,
                        event_id,
                        staff_row["id"],
                    )
                    initialized += 1

            return {
                "event_id": event_id,
                "initialized_count": initialized,
                "total_expected": len(staff_rows),
            }


async def check_in_staff(event_id: str, event_staff_id: str, note: Optional[str] = None) -> dict[str, Any]:
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
                    detail="Impossible de pointer pour cet événement.",
                )

            staff_row = await conn.fetchrow(
                """
                SELECT es.id, es.assignment_status, ea.id AS attendance_id
                FROM event_staff es
                LEFT JOIN event_attendance ea ON ea.event_staff_id = es.id
                WHERE es.id = $1 AND es.event_id = $2
                """,
                event_staff_id,
                event_id,
            )
            if not staff_row:
                raise HTTPException(status_code=404, detail="Affectation introuvable.")
            if staff_row["assignment_status"] != "CONFIRMED":
                raise HTTPException(
                    status_code=400,
                    detail="Seul le personnel confirmé peut être pointé.",
                )

            attendance_id = staff_row["attendance_id"]
            if not attendance_id:
                attendance_id = await conn.fetchval(
                    """
                    INSERT INTO event_attendance (event_id, event_staff_id, status, check_in_at, note)
                    VALUES ($1, $2, 'PRESENT', NOW(), $3)
                    RETURNING id
                    """,
                    event_id,
                    event_staff_id,
                    note,
                )
            else:
                if note is not None:
                    await conn.execute(
                        """
                        UPDATE event_attendance
                        SET status = 'PRESENT', check_in_at = NOW(), note = $2, updated_at = NOW()
                        WHERE id = $1
                        """,
                        attendance_id,
                        note,
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE event_attendance
                        SET status = 'PRESENT', check_in_at = NOW(), updated_at = NOW()
                        WHERE id = $1
                        """,
                        attendance_id,
                    )

            return {"success": True, "attendance_id": str(attendance_id), "message": "Check-in enregistré."}


async def check_out_staff(event_id: str, event_staff_id: str, note: Optional[str] = None) -> dict[str, Any]:
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
                    detail="Impossible de pointer pour cet événement.",
                )

            staff_row = await conn.fetchrow(
                """
                SELECT es.id, es.assignment_status, ea.id AS attendance_id, ea.check_in_at, ea.check_out_at, ea.status
                FROM event_staff es
                JOIN event_attendance ea ON ea.event_staff_id = es.id
                WHERE es.id = $1 AND es.event_id = $2
                """,
                event_staff_id,
                event_id,
            )
            if not staff_row:
                raise HTTPException(status_code=404, detail="Affectation introuvable.")
            if staff_row["assignment_status"] != "CONFIRMED":
                raise HTTPException(
                    status_code=400,
                    detail="Seul le personnel confirmé peut être pointé.",
                )
            if not staff_row["check_in_at"]:
                raise HTTPException(
                    status_code=400,
                    detail="Impossible de faire le check-out sans check-in.",
                )

            if staff_row["check_out_at"] is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Le serveur a déjà fait son check-out.",
                )

            if note is not None:
                await conn.execute(
                    """
                    UPDATE event_attendance
                    SET status = 'LEFT', check_out_at = NOW(), note = $2, updated_at = NOW()
                    WHERE id = $1
                    """,
                    staff_row["attendance_id"],
                    note,
                )
            else:
                await conn.execute(
                    """
                    UPDATE event_attendance
                    SET status = 'LEFT', check_out_at = NOW(), updated_at = NOW()
                    WHERE id = $1
                    """,
                    staff_row["attendance_id"],
                )

            return {"success": True, "attendance_id": str(staff_row["attendance_id"]), "message": "Check-out enregistré."}


async def update_attendance_status(event_id: str, event_staff_id: str, status: str, note: Optional[str] = None) -> dict[str, Any]:
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
                    detail="Impossible de modifier les présences pour cet événement.",
                )

            staff_row = await conn.fetchrow(
                """
                SELECT es.id, es.assignment_status, ea.id AS attendance_id, ea.status AS current_status
                FROM event_staff es
                JOIN event_attendance ea ON ea.event_staff_id = es.id
                WHERE es.id = $1 AND es.event_id = $2
                """,
                event_staff_id,
                event_id,
            )
            if not staff_row:
                raise HTTPException(status_code=404, detail="Affectation introuvable.")
            if staff_row["assignment_status"] != "CONFIRMED":
                raise HTTPException(
                    status_code=400,
                    detail="Seul le personnel confirmé peut être modifié.",
                )

            current_status = staff_row["current_status"]
            allowed = ALLOWED_TRANSITIONS.get(current_status, set())
            if status not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Transition de statut invalide: {current_status} -> {status}.",
                )

            if status in ("PRESENT", "LATE"):
                if note is not None:
                    check_in = await conn.fetchval(
                        """
                        UPDATE event_attendance
                        SET status = $1, check_in_at = COALESCE(check_in_at, NOW()), note = $2, updated_at = NOW()
                        WHERE id = $3
                        RETURNING id
                        """,
                        status,
                        note,
                        staff_row["attendance_id"],
                    )
                else:
                    check_in = await conn.fetchval(
                        """
                        UPDATE event_attendance
                        SET status = $1, check_in_at = COALESCE(check_in_at, NOW()), updated_at = NOW()
                        WHERE id = $2
                        RETURNING id
                        """,
                        status,
                        staff_row["attendance_id"],
                    )
            else:
                if note is not None:
                    check_in = await conn.fetchval(
                        """
                        UPDATE event_attendance
                        SET status = $1, note = $2, updated_at = NOW()
                        WHERE id = $3
                        RETURNING id
                        """,
                        status,
                        note,
                        staff_row["attendance_id"],
                    )
                else:
                    check_in = await conn.fetchval(
                        """
                        UPDATE event_attendance
                        SET status = $1, updated_at = NOW()
                        WHERE id = $2
                        RETURNING id
                        """,
                        status,
                        staff_row["attendance_id"],
                    )

            return {"success": True, "attendance_id": str(check_in), "status": status}


async def get_attendance_summary(event_id: str) -> dict[str, Any]:
    data = await get_event_attendance(event_id)
    summary = data.get("summary", {})
    total = summary.get("total_expected", 0)
    present = summary.get("present", 0)
    late = summary.get("late", 0)
    attendance_rate = data.get("attendance_rate", 0.0)

    return {
        "event_id": event_id,
        "total_expected": total,
        "present": present,
        "late": late,
        "absent": summary.get("absent", 0),
        "excused": summary.get("excused", 0),
        "checked_out": summary.get("checked_out", 0),
        "not_checked_in": summary.get("not_checked_in", 0),
        "attendance_rate": attendance_rate,
    }
