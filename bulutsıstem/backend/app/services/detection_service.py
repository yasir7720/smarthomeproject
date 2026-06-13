import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mqtt_topics import camera_person_topic
from app.database import async_session
from app.models.camera import Camera
from app.models.detection_event import DetectionEvent
from app.services import fcm_service, mqtt_service

logger = logging.getLogger(__name__)

_last_counts: dict[str, int] = {}


async def handle_frigate_person_topic(topic: str, payload: str) -> None:
    """frigate/{stream_key}/person → tenant topic + kayıt + FCM"""
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "frigate" or parts[2] != "person":
        return

    stream_key = parts[1]
    count = int(payload.strip()) if payload.strip().isdigit() else 0
    prev = _last_counts.get(stream_key, 0)

    async with async_session() as db:
        result = await db.execute(select(Camera).where(Camera.stream_key == stream_key))
        camera = result.scalar_one_or_none()
        if camera is None:
            return

        if not camera.alarm_on_person:
            _last_counts[stream_key] = count
            return

        tenant_topic = camera_person_topic(camera.tenant_id, camera.id)
        await mqtt_service.publish_raw(tenant_topic, str(count))

        if count > 0 and prev == 0:
            event = DetectionEvent(
                tenant_id=camera.tenant_id,
                camera_id=camera.id,
                object_type="person",
                count=count,
            )
            db.add(event)
            await db.commit()
            await fcm_service.notify_person_detected(db, camera.tenant_id, camera.name, count)
            logger.info("Kişi algılandı: %s (tenant=%s)", camera.name, camera.tenant_id)

    _last_counts[stream_key] = count


async def list_events(db: AsyncSession, tenant_id: uuid.UUID, limit: int = 50) -> list[DetectionEvent]:
    result = await db.execute(
        select(DetectionEvent)
        .where(DetectionEvent.tenant_id == tenant_id)
        .order_by(DetectionEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
