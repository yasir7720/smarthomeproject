import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.camera import CameraResponse


class IpWebcamCreateRequest(BaseModel):
    name: str = Field(default="Telefon Kamerası", min_length=2, max_length=255)
    phone_ip: str = Field(
        min_length=7,
        max_length=64,
        description="Telefon IP adresi, örn: 192.168.1.105",
        examples=["192.168.1.105"],
    )
    port: int = Field(default=8080, ge=1, le=65535)


class EdgeHeartbeatRequest(BaseModel):
    agent_name: str = Field(default="edge-agent", max_length=100)
    local_ip: str | None = None
    message: str | None = None


class EdgeHeartbeatResponse(BaseModel):
    tenant_id: uuid.UUID
    status: str
    last_seen: datetime


class EdgeInfoResponse(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    edge_agent_key: str
    note: str = "Bu anahtarı edge-agent/config.yaml dosyasına yazın; tunnel.enabled: true ile tünel açılır"


class EdgeIpWebcamRequest(IpWebcamCreateRequest):
    pass


class EdgeTunnelStatusResponse(BaseModel):
    tenant_id: uuid.UUID
    connected: bool
    message: str
