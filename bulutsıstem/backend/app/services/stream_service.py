import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import build_authenticated_stream_url, decrypt_camera_password
from app.models.camera import Camera, CameraProtocol, CameraSourceKind
from app.services import ip_webcam_service, tunnel_service

logger = logging.getLogger(__name__)


def _camera_source(camera: Camera) -> str:
    if camera.source_kind == CameraSourceKind.edge_agent.value:
        return tunnel_service.tunnel_manager.tunnel_mjpeg_url(camera.stream_key)
    if camera.protocol in (CameraProtocol.ip_webcam, CameraProtocol.mjpeg):
        return ip_webcam_service.ip_webcam_go2rtc_source(camera.stream_url)
    password = decrypt_camera_password(camera.password_encrypted)
    return build_authenticated_stream_url(camera.stream_url, camera.username, password)


async def register_camera_stream(camera: Camera) -> tuple[bool, str]:
    src = _camera_source(camera)
    dst = camera.stream_key
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.put(
                f"{settings.go2rtc_url}/api/streams",
                params={"dst": dst, "src": src},
            )
            if response.status_code in (200, 201):
                if camera.protocol == CameraProtocol.ip_webcam:
                    return True, "IP Webcam → go2rtc yayını aktif"
                return True, "go2rtc yayını aktif"
            body = response.text[:200]
            return False, f"go2rtc hata: HTTP {response.status_code} — {body}"
    except httpx.HTTPError as exc:
        logger.warning("go2rtc kayıt hatası: %s", exc)
        return False, f"go2rtc bağlantı hatası: {exc}"


async def unregister_camera_stream(stream_key: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{settings.go2rtc_url}/api/streams",
                params={"src": stream_key},
            )
    except httpx.HTTPError as exc:
        logger.warning("go2rtc silme hatası: %s", exc)


def mjpeg_proxy_url(stream_key: str) -> str:
    return f"{settings.go2rtc_url}/api/stream.mjpeg?src={stream_key}"


async def sync_tenant_edge_cameras(db: AsyncSession, tenant_id) -> None:
    from app.models.camera import CameraSourceKind, CameraStatus

    result = await db.execute(
        select(Camera).where(
            Camera.tenant_id == tenant_id,
            Camera.source_kind == CameraSourceKind.edge_agent.value,
        )
    )
    cameras = result.scalars().all()
    for camera in cameras:
        ok, msg = await register_camera_stream(camera)
        camera.status_message = msg
        camera.status = CameraStatus.active if ok else CameraStatus.error
    await db.commit()


async def sync_all_cameras(db: AsyncSession) -> None:
    from app.models.camera import CameraStatus

    result = await db.execute(select(Camera))
    cameras = result.scalars().all()
    for camera in cameras:
        ok, msg = await register_camera_stream(camera)
        camera.status_message = msg
        if ok:
            camera.status = CameraStatus.active
    await db.commit()
