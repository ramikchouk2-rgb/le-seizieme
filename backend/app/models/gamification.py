from pydantic import BaseModel
from typing import Optional, Any


class RankingItemResponse(BaseModel):
    rank: int
    server_id: str
    server_name: str
    total_points: int
    completion_points: int = 0
    performance_points: int = 0


class RankingResponse(BaseModel):
    year: int
    month: int
    calculated_at: Optional[str] = None
    rankings: list[RankingItemResponse] = []
    total_servers: int = 0
    total_points: int = 0
    top_server: Optional[str] = None
    status: Optional[str] = None


class BonusResponse(BaseModel):
    server_id: str
    server_name: str
    rank: int
    points: int
    bonus_amount: float
    rule: Optional[str] = None
    status: Optional[str] = None


class ServerPointsResponse(BaseModel):
    server_id: str
    server_name: str
    total_points: int
    completion_points: int = 0
    performance_points: int = 0
    current_month_points: int = 0
    previous_month_points: int = 0
    rank: Optional[int] = None
    transactions: list[dict[str, Any]] = []


class PointTransactionResponse(BaseModel):
    transaction_id: str
    server_id: str
    type: str
    points: int
    event_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None


class GamificationCalculationResponse(BaseModel):
    year: int
    month: int
    rankings: list[RankingItemResponse] = []
    total_servers: int = 0
    status: str = "CALCULATED"


class GamificationAwardResponse(BaseModel):
    event_id: str
    status: str
    points_awarded: int
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
