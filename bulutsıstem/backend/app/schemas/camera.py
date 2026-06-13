import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.config import settings
from app.models.camera import CameraProtocol, CameraStatus


class CameraCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    stream_url: str = Field(min_length=5, description="RTSP, MJPEG veya ONVIF stream adresi")
    protocol: CameraProtocol = CameraProtocol.rtsp
    username: str | None = None
    password: str | None = None


class CameraUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    stream_url: str | None = Field(default=None, min_length=5)
    protocol: CameraProtocol | None = None
    username: str | None = None
    password: str | None = None
    status: CameraStatus | None = None


class CameraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    stream_url: str
    protocol: CameraProtocol
    username: str | None
    status: CameraStatus
    status_message: str | None
    stream_key: str
    source_kind: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StreamTokenResponse(BaseModel):
    camera_id: uuid.UUID
    stream_key: str
    stream_token: str
    stream_url: str
    mjpeg_url: str
    expires_in_seconds: int = 900
