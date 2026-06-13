import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import PLAN_LIMITS
from app.models.camera import Camera
from app.models.device import Device
from app.models.tenant import Tenant


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def check_camera_limit(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    tenant = await get_tenant(db, tenant_id)
    if tenant is None:
        return
    limits = PLAN_LIMITS.get(tenant.plan, PLAN_LIMITS["free"])
    result = await db.execute(select(func.count()).select_from(Camera).where(Camera.tenant_id == tenant_id))
    count = result.scalar_one()
    if count >= limits["max_cameras"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Kamera limiti doldu ({limits['max_cameras']}). Plan: {tenant.plan}",
        )


async def check_device_limit(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    tenant = await get_tenant(db, tenant_id)
    if tenant is None:
        return
    limits = PLAN_LIMITS.get(tenant.plan, PLAN_LIMITS["free"])
    result = await db.execute(select(func.count()).select_from(Device).where(Device.tenant_id == tenant_id))
    count = result.scalar_one()
    if count >= limits["max_devices"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cihaz limiti doldu ({limits['max_devices']}). Plan: {tenant.plan}",
        )
