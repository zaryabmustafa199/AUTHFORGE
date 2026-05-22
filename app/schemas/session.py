from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class SessionResponse(BaseModel):
    id: UUID
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    is_revoked: bool
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
