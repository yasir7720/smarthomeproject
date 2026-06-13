import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.tenant import TenantRole


class MemberInviteRequest(BaseModel):
    email: EmailStr
    role: TenantRole = TenantRole.viewer


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: TenantRole
    joined_at: datetime
