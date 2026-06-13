import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_membership, require_role
from app.database import get_db
from app.models.tenant import TenantMember, TenantRole
from app.schemas.device import DeviceCommandRequest, DeviceCreateRequest, DeviceResponse
from app.services import device_service

router = APIRouter(prefix="/tenants/{tenant_id}/devices", tags=["Cihazlar"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> list[DeviceResponse]:
    return await device_service.list_devices(db, membership.tenant_id)


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def add_device(
    data: DeviceCreateRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    return await device_service.create_device(db, membership.tenant_id, data)


@router.post("/{device_id}/command", response_model=DeviceResponse)
async def command_device(
    device_id: uuid.UUID,
    data: DeviceCommandRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin, TenantRole.viewer)),
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    device = await device_service.get_device(db, membership.tenant_id, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cihaz bulunamadı")
    return await device_service.set_device_state(db, device, data.is_on)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> None:
    device = await device_service.get_device(db, membership.tenant_id, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cihaz bulunamadı")
    await device_service.delete_device(db, device)
