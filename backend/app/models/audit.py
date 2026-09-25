from pydantic import BaseModel
from typing import Optional, Any


class AuditLogItem(BaseModel):
    id: str
    actor_user_id: Optional[str] = None
    target_user_id: Optional[str] = None
    action: str
    detail: Optional[dict[str, Any]] = None
    created_at: str
    actor_email: Optional[str] = None
    target_email: Optional[str] = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int
