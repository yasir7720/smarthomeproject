import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CameraProtocol(str, enum.Enum):
    rtsp = "rtsp"
    mjpeg = "mjpeg"
    onvif = "onvif"
    ip_webcam = "ip_webcam"


class CameraSourceKind(str, enum.Enum):
    manual = "manual"
    ip_webcam = "ip_webcam"
    edge_agent = "edge_agent"


class CameraStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    error = "error"
    disabled = "disabled"


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[CameraProtocol] = mapped_column(Enum(CameraProtocol), default=CameraProtocol.rtsp)
    source_kind: Mapped[str] = mapped_column(String(50), default=CameraSourceKind.manual.value)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CameraStatus] = mapped_column(Enum(CameraStatus), default=CameraStatus.pending)
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stream_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    alarm_on_person: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="cameras")


from app.models.tenant import Tenant  # noqa: E402
