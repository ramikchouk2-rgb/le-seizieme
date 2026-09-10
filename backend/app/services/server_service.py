from datetime import datetime, timezone
from typing import Any

from app.core.database import get_pool
from app.utils.datetime_utils import now_naive_utc


SORT_WHITELIST = {
    "first_name": "s.first_name",
    "last_name": "s.last_name",
    "name": "s.first_name",
    "gender": "s.gender",
    "city": "c.name",
    "experience": "s.years_experience",
    "worker_type": "sp.worker_type",
    "availability": "availability_status",
    "skill_level": "main_skill.level",
    "points": "COALESCE(mr.total_points, 0)",
    "vehicle": "v.brand",
    "transport": "v.can_transport_coworkers",
    "location": "sl.is_verified",
}


async def _get_current_month_year() -> tuple[int, int]:
    now = now_naive_utc()
    return now.year, now.month


async def load_server_list(
    search: str | None,
    city: str | None,
    gender: str | None,
    availability: str | None,
    worker_type: str | None,
    has_vehicle: bool | None,
    can_transport: bool | None,
    location_verified: bool | None,
    min_experience: int | None,
    max_experience: int | None,
    skill: str | None,
    sort_by: str | None,
    sort_order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_clauses = ["s.is_active = TRUE"]
        params: list[Any] = []
        idx = 1

        if search:
            where_clauses.append(
                f"(s.first_name ILIKE ${idx} OR s.last_name ILIKE ${idx} OR s.email ILIKE ${idx}"
                f" OR EXISTS (SELECT 1 FROM server_skills ss_search JOIN skills sk_search ON ss_search.skill_id = sk_search.id"
                f" WHERE ss_search.server_id = s.id AND sk_search.name ILIKE ${idx}))"
            )
            params.append(f"%{search}%")
            idx += 1

        if city:
            where_clauses.append(f"c.name = ${idx}")
            params.append(city)
            idx += 1

        if gender:
            where_clauses.append(f"s.gender = ${idx}")
            params.append(gender)
            idx += 1

        if worker_type:
            where_clauses.append(f"sp.worker_type = ${idx}")
            params.append(worker_type)
            idx += 1

        if has_vehicle is not None:
            if has_vehicle:
                where_clauses.append(f"v.id IS NOT NULL")
            else:
                where_clauses.append(f"v.id IS NULL")

        if can_transport is not None:
            where_clauses.append(f"v.can_transport_coworkers = ${idx}")
            params.append(can_transport)
            idx += 1

        if location_verified is not None:
            where_clauses.append(f"sl.is_verified = ${idx}")
            params.append(location_verified)
            idx += 1

        if min_experience is not None:
            where_clauses.append(f"s.years_experience >= ${idx}")
            params.append(min_experience)
            idx += 1

        if max_experience is not None:
            where_clauses.append(f"s.years_experience <= ${idx}")
            params.append(max_experience)
            idx += 1

        if skill:
            where_clauses.append(
                f"EXISTS (SELECT 1 FROM server_skills ss_filter JOIN skills sk_filter ON ss_filter.skill_id = sk_filter.id"
                f" WHERE ss_filter.server_id = s.id AND sk_filter.name = ${idx})"
            )
            params.append(skill)
            idx += 1

        if availability:
            if availability == "AVAILABLE":
                where_clauses.append(
                    f"(sa.start_datetime <= NOW() AND sa.end_datetime > NOW() AND sa.status = 'AVAILABLE')"
                )
            else:
                where_clauses.append(
                    f"(sa.id IS NULL OR sa.end_datetime <= NOW() OR sa.status = 'UNAVAILABLE')"
                )

        where_sql = " AND ".join(where_clauses)
        order_column = SORT_WHITELIST.get(sort_by, "s.first_name")
        order_direction = "ASC" if sort_order == "asc" else "DESC"

        year, month = await _get_current_month_year()

        count_query = f"""
            SELECT COUNT(DISTINCT s.id) AS total
            FROM servers s
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_profile sp ON s.id = sp.server_id
            LEFT JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
            LEFT JOIN vehicles v ON v.owner_server_id = s.id AND v.is_active = TRUE
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= NOW()
                AND sa.end_datetime > NOW()
            WHERE {where_sql}
        """

        total_row = await conn.fetchrow(count_query, *params)
        total = total_row["total"] if total_row else 0

        data_query = f"""
            SELECT
                s.id,
                s.first_name,
                s.last_name,
                s.gender,
                c.name AS city,
                s.years_experience,
                sp.worker_type,
                CASE
                    WHEN sa.start_datetime <= NOW() AND sa.end_datetime > NOW() AND sa.status = 'AVAILABLE'
                    THEN 'AVAILABLE'
                    ELSE 'UNAVAILABLE'
                END AS availability_status,
                sl.is_verified AS location_verified,
                main_skill.name AS main_skill_name,
                main_skill.level AS main_skill_level,
                v.id AS vehicle_id,
                v.brand AS vehicle_brand,
                v.model AS vehicle_model,
                v.can_transport_coworkers AS vehicle_can_transport,
                COALESCE(mr.total_points, 0) AS monthly_points,
                mr.rank
            FROM servers s
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_profile sp ON s.id = sp.server_id
            LEFT JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
            LEFT JOIN vehicles v ON v.owner_server_id = s.id AND v.is_active = TRUE
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= NOW()
                AND sa.end_datetime > NOW()
            LEFT JOIN LATERAL (
                SELECT sk2.name, ss2.level
                FROM server_skills ss2
                JOIN skills sk2 ON ss2.skill_id = sk2.id
                WHERE ss2.server_id = s.id
                ORDER BY ss2.level DESC, sk2.name ASC
                LIMIT 1
            ) main_skill ON TRUE
            LEFT JOIN monthly_rankings mr ON mr.server_id = s.id AND mr.year = ${idx} AND mr.month = ${idx + 1}
            WHERE {where_sql}
            GROUP BY s.id, c.name, sp.worker_type, sa.start_datetime, sa.end_datetime, sa.status,
                     sl.is_verified,
                     main_skill.name, main_skill.level,
                     v.id, v.brand, v.model, v.can_transport_coworkers,
                     mr.total_points, mr.rank
            ORDER BY {order_column} {order_direction}
            LIMIT ${idx + 2} OFFSET ${idx + 3}
        """

        params.extend([year, month, page_size, (page - 1) * page_size])
        rows = await conn.fetch(data_query, *params)

        result = []
        for r in rows:
            item: dict[str, Any] = {
                "id": str(r["id"]),
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "gender": r["gender"],
                "city": r["city"],
                "years_experience": r["years_experience"],
                "worker_type": r["worker_type"] or "",
                "availability_status": r["availability_status"],
                "main_skill": r["main_skill_name"] or "",
                "main_skill_level": r["main_skill_level"] or 0,
                "location_verified": bool(r["location_verified"]),
                "monthly_points": r["monthly_points"],
                "rank": r["rank"] or 0,
            }
            if r["vehicle_id"]:
                item["vehicle"] = {
                    "brand": r["vehicle_brand"],
                    "model": r["vehicle_model"],
                    "can_transport_coworkers": r["vehicle_can_transport"],
                }
            result.append(item)

        return result, total


async def load_server_detail(server_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        server_row = await conn.fetchrow(
            """
            SELECT s.id, s.first_name, s.last_name, s.gender, s.email, s.phone,
                   c.name AS city, s.years_experience,
                   sp.worker_type,
                   CASE
                       WHEN sa.start_datetime <= NOW() AND sa.end_datetime > NOW() AND sa.status = 'AVAILABLE'
                       THEN 'AVAILABLE'
                       ELSE 'UNAVAILABLE'
                   END AS availability_status,
                   sl.area AS location_area,
                   sl.is_verified AS location_verified
            FROM servers s
            JOIN cities c ON s.city_id = c.id
            LEFT JOIN server_profile sp ON s.id = sp.server_id
            LEFT JOIN server_locations sl ON s.id = sl.server_id AND sl.is_current = TRUE
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= NOW()
                AND sa.end_datetime > NOW()
            WHERE s.id = $1
            LIMIT 1
            """,
            server_id,
        )
        if not server_row:
            return None

        skills_rows = await conn.fetch(
            """
            SELECT sk.name, ss.level
            FROM server_skills ss
            JOIN skills sk ON ss.skill_id = sk.id
            WHERE ss.server_id = $1
            ORDER BY ss.level DESC, sk.name ASC
            """,
            server_id,
        )

        vehicle_row = await conn.fetchrow(
            """
            SELECT id, vehicle_type, brand, model, seats_total, can_transport_coworkers, is_active
            FROM vehicles
            WHERE owner_server_id = $1 AND is_active = TRUE
            LIMIT 1
            """,
            server_id,
        )

        availability_rows = await conn.fetch(
            """
            SELECT id, start_datetime, end_datetime, status
            FROM server_availability
            WHERE server_id = $1
            ORDER BY start_datetime ASC
            """,
            server_id,
        )

        year, month = await _get_current_month_year()
        points_row = await conn.fetchrow(
            """
            SELECT total_points, rank
            FROM monthly_rankings
            WHERE server_id = $1 AND year = $2 AND month = $3
            """,
            server_id,
            year,
            month,
        )

        curr_month_start = datetime(year, month, 1)
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime(year, month + 1, 1)

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_month_start = datetime(prev_year, prev_month, 1)

        current_month_points_row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(points), 0) AS total_points
            FROM point_transactions
            WHERE server_id = $1
              AND created_at >= $2
              AND created_at < $3
            """,
            server_id,
            curr_month_start,
            next_month_start,
        )

        previous_month_points_row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(points), 0) AS total_points
            FROM point_transactions
            WHERE server_id = $1
              AND created_at >= $2
              AND created_at < $3
            """,
            server_id,
            prev_month_start,
            curr_month_start,
        )

        current_month_points = current_month_points_row["total_points"] if current_month_points_row else 0
        previous_month_points = previous_month_points_row["total_points"] if previous_month_points_row else 0
        total_points = current_month_points + previous_month_points

        return {
            "id": str(server_row["id"]),
            "first_name": server_row["first_name"],
            "last_name": server_row["last_name"],
            "gender": server_row["gender"],
            "city": server_row["city"],
            "years_experience": server_row["years_experience"],
            "worker_type": server_row["worker_type"] or "",
            "availability_status": server_row["availability_status"],
            "email": server_row["email"],
            "phone": server_row["phone"],
            "location": {
                "city": server_row["city"],
                "area": server_row["location_area"] or "",
                "is_verified": bool(server_row["location_verified"]),
            },
            "skills": [
                {"name": r["name"], "level": r["level"]} for r in skills_rows
            ],
            "vehicle": {
                "id": str(vehicle_row["id"]),
                "vehicle_type": vehicle_row["vehicle_type"],
                "brand": vehicle_row["brand"],
                "model": vehicle_row["model"],
                "seats_total": vehicle_row["seats_total"],
                "can_transport_coworkers": vehicle_row["can_transport_coworkers"],
                "is_active": vehicle_row["is_active"],
            } if vehicle_row else None,
            "availability": [
                {
                    "id": str(r["id"]),
                    "start_datetime": r["start_datetime"].isoformat() if isinstance(r["start_datetime"], datetime) else str(r["start_datetime"]),
                    "end_datetime": r["end_datetime"].isoformat() if isinstance(r["end_datetime"], datetime) else str(r["end_datetime"]),
                    "status": r["status"],
                }
                for r in availability_rows
            ],
            "points": {
                "total_points": total_points,
                "current_month_points": current_month_points,
                "previous_month_points": previous_month_points,
                "rank": points_row["rank"] if points_row else None,
            },
        }


async def load_server_stats() -> dict[str, int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE s.is_active = TRUE) AS total,
                COUNT(*) FILTER (
                    WHERE s.is_active = TRUE
                    AND sa.start_datetime <= NOW()
                    AND sa.end_datetime > NOW()
                    AND sa.status = 'AVAILABLE'
                ) AS available,
                COUNT(*) FILTER (
                    WHERE s.is_active = TRUE
                    AND (sa.id IS NULL OR sa.end_datetime <= NOW() OR sa.status = 'UNAVAILABLE')
                ) AS unavailable,
                COUNT(*) FILTER (WHERE s.is_active = TRUE AND v.id IS NOT NULL) AS with_vehicle
            FROM servers s
            LEFT JOIN server_availability sa ON s.id = sa.server_id
                AND sa.start_datetime <= NOW()
                AND sa.end_datetime > NOW()
            LEFT JOIN vehicles v ON v.owner_server_id = s.id AND v.is_active = TRUE
            """
        )
        return {
            "total": row["total"] if row else 0,
            "available": row["available"] if row else 0,
            "unavailable": row["unavailable"] if row else 0,
            "with_vehicle": row["with_vehicle"] if row else 0,
        }
