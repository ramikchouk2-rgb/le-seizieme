from typing import Any

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user_dep
from app.models.dashboard import ActivityItemResponse
from app.services.dashboard_service import load_recent_activity

router = APIRouter()


@router.get("/activity/recent", response_model=list[ActivityItemResponse], dependencies=[Depends(get_current_user_dep)])
async def get_recent_activity(limit: int = 10) -> list[ActivityItemResponse]:
    items = await load_recent_activity(limit)
    return [ActivityItemResponse(**item) for item in items]
