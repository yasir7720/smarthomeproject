import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.device import DeviceType


class DeviceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    room: str = Field(min_length=2, max_length=100)
    device_slug: str | None = Field(default=None, max_length=100)
    device_type: DeviceType = DeviceType.other


class DeviceCommandRequest(BaseModel):
    is_on: bool


class DeviceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    room: str
    device_slug: str
    device_type: DeviceType
    mqtt_topic: str
    is_on: bool
    created_at: datetime

    model_config = {"from_attributes": True}
