from pydantic import BaseModel
from typing import Optional


class ActivityItemResponse(BaseModel):
    id: str
    type: str
    message: str
    timestamp: str
    event_id: Optional[str] = None
