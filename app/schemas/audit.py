"""
Audit Log Schemas — Response models for audit trail endpoints.
"""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class AuditLogResponse(BaseModel):
    """Single audit log entry."""
    id: int
    user_id: Optional[UUID] = None
    action: str
    ip_address: Optional[str] = None
    metadata_info: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated list of audit logs for admin endpoints."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    per_page: int
