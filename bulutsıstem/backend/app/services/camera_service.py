import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_camera_password, generate_stream_key
from app.models.camera import Camera, CameraProtocol, CameraSourceKind, CameraStatus
from app.schemas.camera import CameraCreateRequest, CameraUpdateRequest
from app.schemas.edge import IpWebcamCreateRequest
from app.services import frigate_config_service, ip_webcam_service, plan_service, stream_service, tunnel_service


async def _sync_frigate(db: AsyncSession, camera: Camera) -> None:
    ok, msg = await frigate_config_service.sync_config(db)
    if ok:
        camera.status_message = f"{camera.status_message or ''} | {msg}".strip(" |")
        await db.commit()
        await db.refresh(camera)


async def validate_stream_reachable(stream_url: str, protocol: CameraProtocol) -> tuple[bool, str]:
    if protocol in (CameraProtocol.mjpeg, CameraProtocol.ip_webcam):
        return await ip_webcam_service.probe_ip_webcam(stream_url)
    if protocol == CameraProtocol.mjpeg and stream_url.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(stream_url)
                if response.status_code < 500:
                    return True, "MJPEG endpoint erişilebilir"
                return False, f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            return False, f"Bağlantı hatası: {exc}"
    return True, "Stream kaydı go2rtc'ye aktarılacak"


async def _finalize_camera(db: AsyncSession, camera: Camera) -> Camera:
    reg_ok, reg_msg = await stream_service.register_camera_stream(camera)
    camera.status = CameraStatus.active if reg_ok else CameraStatus.error
    camera.status_message = reg_msg
    await db.commit()
    await db.refresh(camera)
    return camera


async def create_camera(db: AsyncSession, tenant_id: uuid.UUID, data: CameraCreateRequest) -> Camera:
    await plan_service.check_camera_limit(db, tenant_id)
    ok, message = await validate_stream_reachable(data.stream_url, data.protocol)
    camera = Camera(
        tenant_id=tenant_id,
        name=data.name,
        stream_url=data.stream_url,
        protocol=data.protocol,
        username=data.username,
        password_encrypted=encrypt_camera_password(data.password),
        status=CameraStatus.pending,
        status_message=message,
        stream_key=generate_stream_key(),
        source_kind=CameraSourceKind.manual.value,
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    if not ok:
        camera.status = CameraStatus.error
        await db.commit()
        await db.refresh(camera)
        return camera
    camera = await _finalize_camera(db, camera)
    await _sync_frigate(db, camera)
    return camera


async def create_ip_webcam_camera(
    db: AsyncSession, tenant_id: uuid.UUID, data: IpWebcamCreateRequest, source_kind: str = CameraSourceKind.ip_webcam.value
) -> Camera:
    await plan_service.check_camera_limit(db, tenant_id)
    stream_url = ip_webcam_service.build_ip_webcam_url(data.phone_ip, data.port)
    if source_kind == CameraSourceKind.edge_agent.value:
        connected = tunnel_service.tunnel_manager.is_connected(tenant_id)
        ok = True
        message = "Edge tünel aktif — yayın hazırlanıyor" if connected else "Kamera kayıtlı; edge agent tüneli bekleniyor"
    else:
        ok, message = await ip_webcam_service.probe_ip_webcam(stream_url)
    camera = Camera(
        tenant_id=tenant_id,
        name=data.name,
        stream_url=stream_url,
        protocol=CameraProtocol.ip_webcam,
        status=CameraStatus.pending,
        status_message=message,
        stream_key=generate_stream_key(),
        source_kind=source_kind,
    )
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    if not ok:
        camera.status = CameraStatus.error
        await db.commit()
        await db.refresh(camera)
        return camera
    if source_kind == CameraSourceKind.edge_agent.value and not tunnel_service.tunnel_manager.is_connected(tenant_id):
        camera.status = CameraStatus.pending
        await db.commit()
        await db.refresh(camera)
        await _sync_frigate(db, camera)
        return camera
    camera = await _finalize_camera(db, camera)
    await _sync_frigate(db, camera)
    return camera


async def list_cameras(db: AsyncSession, tenant_id: uuid.UUID) -> list[Camera]:
    result = await db.execute(
        select(Camera).where(Camera.tenant_id == tenant_id).order_by(Camera.created_at.desc())
    )
    return list(result.scalars().all())


async def get_camera(db: AsyncSession, tenant_id: uuid.UUID, camera_id: uuid.UUID) -> Camera | None:
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id, Camera.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def get_camera_by_stream_key(db: AsyncSession, stream_key: str) -> Camera | None:
    result = await db.execute(select(Camera).where(Camera.stream_key == stream_key))
    return result.scalar_one_or_none()


async def update_camera(db: AsyncSession, camera: Camera, data: CameraUpdateRequest) -> Camera:
    if data.name is not None:
        camera.name = data.name
    if data.stream_url is not None:
        camera.stream_url = data.stream_url
    if data.protocol is not None:
        camera.protocol = data.protocol
    if data.username is not None:
        camera.username = data.username
    if data.password is not None:
        camera.password_encrypted = encrypt_camera_password(data.password)
    if data.status is not None:
        camera.status = data.status

    if data.stream_url is not None or data.protocol is not None:
        ok, message = await validate_stream_reachable(camera.stream_url, camera.protocol)
        if not ok:
            camera.status = CameraStatus.error
            camera.status_message = message
            await db.commit()
            await db.refresh(camera)
            return camera

    await db.commit()
    await db.refresh(camera)
    camera = await _finalize_camera(db, camera)
    await _sync_frigate(db, camera)
    return camera


async def delete_camera(db: AsyncSession, camera: Camera) -> None:
    await stream_service.unregister_camera_stream(camera.stream_key)
    await db.delete(camera)
    await db.commit()
    await frigate_config_service.sync_config(db)
