import math
from datetime import datetime, date, timezone
from typing import Any

from app.core.database import get_pool
from app.utils.datetime_utils import now_naive_utc
from app.utils.event_utils import load_event

POINTS_EVENT_COMPLETION_BASE = 50
POINTS_EVENT_COMPLETION_PER_GUEST = 0.5
POINTS_PERFORMANCE_MULTIPLIER = 2.0
POINTS_PUNCTUALITY_BONUS = 20
POINTS_TEAMWORK_BONUS = 15
POINTS_EVALUATION_THRESHOLD = 7.0


async def load_event_staff(event_id: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, event_id, server_id, role, assignment_status, assigned_at, confirmed_at
            FROM event_staff
            WHERE event_id = $1
            """,
            event_id,
        )
        return [dict(r) for r in rows]


async def load_evaluations(event_id: str) -> dict[str, dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, event_id, server_id, punctuality, work_quality, presentation,
                   teamwork, client_relation, comment, created_at
            FROM evaluations
            WHERE event_id = $1
            """,
            event_id,
        )
        evaluations: dict[str, dict[str, Any]] = {}
        for r in rows:
            evaluations[str(r["server_id"])] = dict(r)
        return evaluations


async def load_server_names(server_ids: list[str]) -> dict[str, str]:
    if not server_ids:
        return {}
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, first_name, last_name
            FROM servers
            WHERE id = ANY($1::uuid[])
            """,
            server_ids,
        )
        return {str(r["id"]): f"{r['first_name']} {r['last_name']}" for r in rows}


async def get_existing_completion_points(event_id: str, server_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id
            FROM point_transactions
            WHERE event_id = $1
              AND server_id = $2
              AND transaction_type = 'EARNED'
              AND reason LIKE $3
            LIMIT 1
            """,
            event_id,
            server_id,
            "Completion:%",
        )
        return row is not None


async def create_point_transaction(
    server_id: str,
    event_id: str | None,
    points: int,
    transaction_type: str,
    reason: str,
    created_by: str | None = None,
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO point_transactions (server_id, event_id, points, transaction_type, reason, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, server_id, event_id, points, transaction_type, reason, created_by, created_at
            """,
            server_id,
            event_id,
            points,
            transaction_type,
            reason,
            created_by,
        )
        return dict(row)


async def calculate_server_points(server_id: str, year: int, month: int) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)

        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(points), 0) AS total_points,
                COALESCE(SUM(points) FILTER (WHERE transaction_type = 'EARNED'), 0) AS completion_points,
                COALESCE(SUM(points) FILTER (WHERE transaction_type = 'BONUS'), 0) AS performance_points,
                count(*) FILTER (WHERE transaction_type = 'EARNED') AS earned_count,
                count(*) FILTER (WHERE transaction_type = 'BONUS') AS bonus_count,
                count(*) FILTER (WHERE transaction_type = 'PENALTY') AS penalty_count,
                count(*) FILTER (WHERE transaction_type = 'ADJUSTMENT') AS adjustment_count
            FROM point_transactions
            WHERE server_id = $1
              AND created_at >= $2
              AND created_at < $3
            """,
            server_id,
            month_start,
            month_end,
        )
        return dict(row) if row else {
            "total_points": 0,
            "completion_points": 0,
            "performance_points": 0,
            "earned_count": 0,
            "bonus_count": 0,
            "penalty_count": 0,
            "adjustment_count": 0,
        }


async def calculate_monthly_rankings(year: int, month: int) -> dict[str, Any]:
    pool = await get_pool()
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                s.id AS server_id,
                s.first_name,
                s.last_name,
                COALESCE(SUM(pt.points), 0) AS total_points,
                COALESCE(SUM(pt.points) FILTER (WHERE pt.transaction_type = 'EARNED'), 0) AS completion_points,
                COALESCE(SUM(pt.points) FILTER (WHERE pt.transaction_type = 'BONUS'), 0) AS performance_points
            FROM servers s
            LEFT JOIN point_transactions pt
                ON s.id = pt.server_id
                AND pt.created_at >= $1
                AND pt.created_at < $2
            GROUP BY s.id, s.first_name, s.last_name
            ORDER BY total_points DESC, s.id ASC
            """,
            month_start,
            month_end,
        )

        rankings: list[dict[str, Any]] = []
        current_rank = 0
        previous_points = None
        inserted = 0
        for idx, row in enumerate(rows, start=1):
            points = row["total_points"]
            if points != previous_points:
                current_rank = idx
                previous_points = points
            rankings.append({
                "server_id": str(row["server_id"]),
                "server_name": f"{row['first_name']} {row['last_name']}",
                "rank": current_rank,
                "total_points": points,
                "completion_points": row["completion_points"],
                "performance_points": row["performance_points"],
            })

        for rank in rankings:
            await conn.execute(
                """
                INSERT INTO monthly_rankings (server_id, year, month, total_points, rank, status)
                VALUES ($1, $2, $3, $4, $5, 'CALCULATED')
                ON CONFLICT (server_id, year, month) DO UPDATE SET
                    total_points = EXCLUDED.total_points,
                    rank = EXCLUDED.rank,
                    status = EXCLUDED.status
                """,
                rank["server_id"],
                year,
                month,
                rank["total_points"],
                rank["rank"],
            )
            inserted += 1

        return {
            "year": year,
            "month": month,
            "rankings": rankings,
            "total_servers": inserted,
        }


async def calculate_bonuses(year: int, month: int) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rankings = await conn.fetch(
            """
            SELECT mr.server_id, mr.rank, mr.total_points,
                   s.first_name, s.last_name
            FROM monthly_rankings mr
            JOIN servers s ON mr.server_id = s.id
            WHERE mr.year = $1 AND mr.month = $2
            ORDER BY mr.rank ASC, s.id ASC
            """,
            year,
            month,
        )

        rules = await conn.fetch(
            """
            SELECT id, name, min_points, max_points, rank_from, rank_to, bonus_amount, active
            FROM bonus_rules
            WHERE active = TRUE
            ORDER BY rank_from ASC
            """
        )
        rules_list = [dict(r) for r in rules]

        bonuses: list[dict[str, Any]] = []
        for rank_row in rankings:
            server_id = str(rank_row["server_id"])
            rank = rank_row["rank"]
            points = rank_row["total_points"]
            bonus_amount = 0.0
            matched_rule = None
            for rule in rules_list:
                if rank >= rule["rank_from"] and rank <= rule["rank_to"]:
                    if points >= rule["min_points"] and points <= rule["max_points"]:
                        bonus_amount = float(rule["bonus_amount"])
                        matched_rule = rule["name"]
                        break

            bonuses.append({
                "server_id": server_id,
                "server_name": f"{rank_row['first_name']} {rank_row['last_name']}",
                "rank": rank,
                "points": points,
                "bonus_amount": bonus_amount,
                "rule": matched_rule,
            })

        return {
            "year": year,
            "month": month,
            "bonuses": bonuses,
            "total_servers": len(bonuses),
        }


async def award_completion_points(event_id: str, created_by: str | None = None) -> dict[str, Any]:
    event = await load_event(event_id)
    if not event:
        return {"error": "Event not found", "status": "ERROR"}

    if event["status"] != "COMPLETED":
        return {"error": "Event is not completed", "status": "ERROR"}

    staff = await load_event_staff(event_id)
    if not staff:
        return {"error": "No staff assigned to event", "status": "ERROR"}

    base_points = POINTS_EVENT_COMPLETION_BASE
    guest_bonus = math.floor(event["guest_count"] * POINTS_EVENT_COMPLETION_PER_GUEST)
    total_event_points = base_points + guest_bonus

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for member in staff:
        if member["assignment_status"] != "CONFIRMED":
            skipped.append({
                "server_id": str(member["server_id"]),
                "reason": "Not confirmed",
            })
            continue

        if await get_existing_completion_points(event_id, str(member["server_id"])):
            skipped.append({
                "server_id": str(member["server_id"]),
                "reason": "Already awarded completion points",
            })
            continue

        tx = await create_point_transaction(
            server_id=str(member["server_id"]),
            event_id=event_id,
            points=total_event_points,
            transaction_type="EARNED",
            reason=f"Completion:{event['name']}",
            created_by=created_by,
        )
        created.append(tx)

    server_names = await load_server_names([str(m["server_id"]) for m in staff])
    created_summary = [
        {
            "server_id": tx["server_id"],
            "server_name": server_names.get(str(tx["server_id"]), "Unknown"),
            "points": tx["points"],
            "reason": tx["reason"],
        }
        for tx in created
    ]

    return {
        "event_id": event_id,
        "status": "SUCCESS",
        "points_awarded": total_event_points,
        "created": created_summary,
        "skipped": skipped,
    }


async def award_performance_points(event_id: str, created_by: str | None = None) -> dict[str, Any]:
    event = await load_event(event_id)
    if not event:
        return {"error": "Event not found", "status": "ERROR"}

    evaluations = await load_evaluations(event_id)
    if not evaluations:
        return {"error": "No evaluations found for event", "status": "ERROR"}

    staff = await load_event_staff(event_id)
    if not staff:
        return {"error": "No staff assigned to event", "status": "ERROR"}

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for member in staff:
        if member["assignment_status"] != "CONFIRMED":
            skipped.append({
                "server_id": str(member["server_id"]),
                "reason": "Not confirmed",
            })
            continue

        evaluation = evaluations.get(str(member["server_id"]))
        if not evaluation:
            skipped.append({
                "server_id": str(member["server_id"]),
                "reason": "No evaluation",
            })
            continue

        avg_score = (
            evaluation["punctuality"]
            + evaluation["work_quality"]
            + evaluation["presentation"]
            + evaluation["teamwork"]
            + evaluation["client_relation"]
        ) / 5.0

        if avg_score < POINTS_EVALUATION_THRESHOLD:
            skipped.append({
                "server_id": str(member["server_id"]),
                "reason": f"Average score {avg_score:.1f} below threshold {POINTS_EVALUATION_THRESHOLD}",
            })
            continue

        bonus_points = math.floor(avg_score * POINTS_PERFORMANCE_MULTIPLIER)
        tx = await create_point_transaction(
            server_id=str(member["server_id"]),
            event_id=event_id,
            points=bonus_points,
            transaction_type="BONUS",
            reason=f"Performance:{event['name']}",
            created_by=created_by,
        )
        created.append(tx)

    server_names = await load_server_names([str(m["server_id"]) for m in staff])
    created_summary = [
        {
            "server_id": tx["server_id"],
            "server_name": server_names.get(str(tx["server_id"]), "Unknown"),
            "points": tx["points"],
            "reason": tx["reason"],
        }
        for tx in created
    ]

    return {
        "event_id": event_id,
        "status": "SUCCESS",
        "evaluations_processed": len(created),
        "created": created_summary,
        "skipped": skipped,
    }


async def get_server_points(server_id: str) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        server = await conn.fetchrow(
            "SELECT id, first_name, last_name FROM servers WHERE id = $1",
            server_id,
        )
        if not server:
            return {"error": "Server not found", "status": "ERROR"}

        now = now_naive_utc()
        current_month = now.month
        current_year = now.year
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        current_points = await calculate_server_points(server_id, current_year, current_month)
        previous_points = await calculate_server_points(server_id, prev_year, prev_month)

        current_month_ranking = await conn.fetchrow(
            """
            SELECT rank, total_points
            FROM monthly_rankings
            WHERE server_id = $1 AND year = $2 AND month = $3
            """,
            server_id,
            current_year,
            current_month,
        )

        total_points = current_points["total_points"] + previous_points["total_points"]

        transactions_rows = await conn.fetch(
            """
            SELECT id, server_id, event_id, points, transaction_type, reason, created_by, created_at
            FROM point_transactions
            WHERE server_id = $1
            ORDER BY created_at DESC
            LIMIT 50
            """,
            server_id,
        )
        transactions = [
            {
                "transaction_id": str(t["id"]),
                "server_id": str(t["server_id"]),
                "event_id": str(t["event_id"]) if t["event_id"] else None,
                "points": t["points"],
                "type": t["transaction_type"],
                "description": t["reason"],
                "created_at": t["created_at"].isoformat() if t["created_at"] else None,
            }
            for t in transactions_rows
        ]

        return {
            "server_id": server_id,
            "server_name": f"{server['first_name']} {server['last_name']}",
            "total_points": total_points,
            "completion_points": current_points.get("completion_points", 0) + previous_points.get("completion_points", 0),
            "performance_points": current_points.get("performance_points", 0) + previous_points.get("performance_points", 0),
            "current_month_points": current_points["total_points"],
            "previous_month_points": previous_points["total_points"],
            "rank": current_month_ranking["rank"] if current_month_ranking else None,
            "transactions": transactions,
        }
