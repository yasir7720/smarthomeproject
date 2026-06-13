import logging
from pathlib import Path

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import decrypt_secret
from app.core.security import build_authenticated_stream_url
from app.models.camera import Camera, CameraProtocol, CameraSourceKind, CameraStatus
from app.services.tunnel_service import tunnel_manager

logger = logging.getLogger(__name__)


def _camera_source(camera: Camera) -> str:
    if camera.source_kind == CameraSourceKind.edge_agent.value:
        return tunnel_manager.tunnel_mjpeg_url(camera.stream_key)
    password = decrypt_secret(camera.password_encrypted)
    return build_authenticated_stream_url(camera.stream_url, camera.username, password)


def _frigate_camera_entry(camera: Camera) -> dict:
    source = _camera_source(camera)
    entry: dict = {
        "ffmpeg": {
            "inputs": [{"path": source, "roles": ["detect"]}],
        },
        "detect": {"enabled": True, "width": 1280, "height": 720, "fps": 10},
        "objects": {"track": ["person"]},
        "snapshots": {"enabled": True, "bounding_box": True},
    }
    if camera.protocol in (CameraProtocol.mjpeg, CameraProtocol.ip_webcam):
        entry["ffmpeg"]["input_args"] = "preset-http-mjpeg-generic"
    return entry


async def build_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Camera).where(Camera.status != CameraStatus.disabled))
    cameras = result.scalars().all()
    camera_configs = {}
    for cam in cameras:
        camera_configs[cam.stream_key] = _frigate_camera_entry(cam)

    return {
        "mqtt": {
            "enabled": True,
            "host": "127.0.0.1",
            "port": settings.public_mqtt_port,
            "user": settings.mqtt_frigate_user,
            "password": settings.mqtt_frigate_password,
        },
        "cameras": camera_configs,
        "version": "0.14",
    }


async def sync_config(db: AsyncSession) -> tuple[bool, str]:
    config = await build_config(db)
    config_path = Path(settings.frigate_config_path)
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        logger.info("Frigate config yazıldı: %s (%d kamera)", config_path, len(config["cameras"]))
    except OSError as exc:
        return False, f"Config yazılamadı: {exc}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{settings.frigate_api_url}/api/restart")
        return True, f"Frigate güncellendi ({len(config['cameras'])} kamera)"
    except httpx.HTTPError:
        return True, f"Config yazıldı; Frigate yeniden başlatma bekleniyor ({len(config['cameras'])} kamera)"
