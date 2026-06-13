import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mqtt_topics import device_topic
from app.models.device import Device, DeviceType
from app.schemas.device import DeviceCreateRequest
from app.services import mqtt_service, plan_service


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "cihaz"


async def create_device(db: AsyncSession, tenant_id: uuid.UUID, data: DeviceCreateRequest) -> Device:
    await plan_service.check_device_limit(db, tenant_id)
    slug = data.device_slug or _slugify(data.name)
    topic = device_topic(tenant_id, data.room, slug)
    device = Device(
        tenant_id=tenant_id,
        name=data.name,
        room=data.room,
        device_slug=slug,
        device_type=data.device_type,
        mqtt_topic=topic,
        is_on=False,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def list_devices(db: AsyncSession, tenant_id: uuid.UUID) -> list[Device]:
    result = await db.execute(
        select(Device).where(Device.tenant_id == tenant_id).order_by(Device.room, Device.name)
    )
    return list(result.scalars().all())


async def get_device(db: AsyncSession, tenant_id: uuid.UUID, device_id: uuid.UUID) -> Device | None:
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def set_device_state(db: AsyncSession, device: Device, is_on: bool) -> Device:
    device.is_on = is_on
    payload = {"durum": "acik" if is_on else "kapali"}
    await mqtt_service.publish(device.mqtt_topic, payload)
    await db.commit()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device: Device) -> None:
    await db.delete(device)
    await db.commit()


async def seed_default_devices(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    defaults = [
        ("Ana Lamba", "salon", "lamba", DeviceType.light),
        ("TV Priz", "salon", "tv", DeviceType.tv),
        ("Tavan Lambası", "yatakodasi", "lamba", DeviceType.light),
        ("Kahve Makinesi", "mutfak", "priz", DeviceType.outlet),
    ]
    for name, room, slug, dtype in defaults:
        topic = device_topic(tenant_id, room, slug)
        device = Device(
            tenant_id=tenant_id,
            name=name,
            room=room,
            device_slug=slug,
            device_type=dtype,
            mqtt_topic=topic,
        )
        db.add(device)
    await db.commit()
