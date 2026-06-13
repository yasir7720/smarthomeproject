import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.tenant import TenantRole


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    role: TenantRole
    created_at: datetime

    model_config = {"from_attributes": True}


class MqttCredentialsResponse(BaseModel):
    host: str
    port: int
    username: str
    password: str
    topic_prefix: str
