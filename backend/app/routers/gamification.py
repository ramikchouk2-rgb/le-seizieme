from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_pool
from app.core.deps import require_manager_or_admin, get_current_user_dep
from app.models.gamification import (
    BonusResponse,
    GamificationAwardResponse,
    GamificationCalculationResponse,
    RankingResponse,
    ServerPointsResponse,
)
from app.services.gamification_engine import (
    award_completion_points,
    award_performance_points,
    calculate_bonuses,
    calculate_monthly_rankings,
    get_server_points,
)
from app.services.gamification_engine import calculate_server_points

router = APIRouter()


@router.post("/events/{event_id}/award-completion-points", response_model=GamificationAwardResponse, dependencies=[Depends(require_manager_or_admin)])
async def award_completion(event_id: str) -> GamificationAwardResponse:
    result = await award_completion_points(event_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    return GamificationAwardResponse(**result)


@router.post("/events/{event_id}/award-performance-points", response_model=GamificationAwardResponse, dependencies=[Depends(require_manager_or_admin)])
async def award_performance(event_id: str) -> GamificationAwardResponse:
    result = await award_performance_points(event_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    return GamificationAwardResponse(**result)


@router.get("/servers/{server_id}/points", response_model=ServerPointsResponse, dependencies=[Depends(get_current_user_dep)])
async def server_points(server_id: str) -> ServerPointsResponse:
    result = await get_server_points(server_id)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=404, detail=result.get("error", "Server not found"))
    return ServerPointsResponse(**result)


@router.post("/rankings/{year}/{month}/calculate", response_model=GamificationCalculationResponse, dependencies=[Depends(require_manager_or_admin)])
async def calculate_rankings(year: int, month: int) -> GamificationCalculationResponse:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")
    result = await calculate_monthly_rankings(year, month)
    return GamificationCalculationResponse(**result)


@router.get("/rankings/{year}/{month}", response_model=RankingResponse, dependencies=[Depends(get_current_user_dep)])
async def get_rankings(year: int, month: int) -> RankingResponse:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT mr.rank, mr.total_points, mr.status,
                   s.id AS server_id, s.first_name, s.last_name,
                   COALESCE(SUM(pt.points) FILTER (WHERE pt.transaction_type = 'EARNED'), 0) AS completion_points,
                   COALESCE(SUM(pt.points) FILTER (WHERE pt.transaction_type = 'BONUS'), 0) AS performance_points
            FROM monthly_rankings mr
            JOIN servers s ON mr.server_id = s.id
            LEFT JOIN point_transactions pt
                ON pt.server_id = s.id
                AND pt.created_at >= make_date(mr.year, mr.month, 1)
                AND pt.created_at < (make_date(mr.year, mr.month, 1) + INTERVAL '1 month')
            WHERE mr.year = $1 AND mr.month = $2
            GROUP BY mr.rank, mr.total_points, mr.status, s.id, s.first_name, s.last_name
            ORDER BY mr.rank ASC, s.id ASC
            """,
            year,
            month,
        )
        rankings = []
        total_points = 0
        top_server = None
        for r in rows:
            total_points += r["total_points"]
            if not top_server:
                top_server = f"{r['first_name']} {r['last_name']}"
            rankings.append({
                "rank": r["rank"],
                "server_id": str(r["server_id"]),
                "server_name": f"{r['first_name']} {r['last_name']}",
                "total_points": r["total_points"],
                "completion_points": r["completion_points"],
                "performance_points": r["performance_points"],
            })
        return RankingResponse(
            year=year,
            month=month,
            rankings=rankings,
            total_servers=len(rankings),
            total_points=total_points,
            top_server=top_server,
            status=rows[0]["status"] if rows else None,
        )


@router.get("/bonuses/{year}/{month}", response_model=list[BonusResponse], dependencies=[Depends(get_current_user_dep)])
async def get_bonuses(year: int, month: int) -> list[BonusResponse]:
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")
    result = await calculate_bonuses(year, month)
    return [BonusResponse(**b) for b in result.get("bonuses", [])]
