import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_tenant_membership, require_role
from app.config import settings
from app.core.security import create_stream_token
from app.database import get_db
from app.models.tenant import TenantMember, TenantRole
from app.models.user import User
from app.schemas.camera import (
    CameraCreateRequest,
    CameraResponse,
    CameraUpdateRequest,
    StreamTokenResponse,
)
from app.services import camera_service

router = APIRouter(prefix="/tenants/{tenant_id}/cameras", tags=["Kameralar"])


@router.get("", response_model=list[CameraResponse])
async def list_cameras(
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> list[CameraResponse]:
    return await camera_service.list_cameras(db, membership.tenant_id)


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def add_camera(
    data: CameraCreateRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> CameraResponse:
    return await camera_service.create_camera(db, membership.tenant_id, data)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: uuid.UUID,
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> CameraResponse:
    camera = await camera_service.get_camera(db, membership.tenant_id, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
    return camera


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: uuid.UUID,
    data: CameraUpdateRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> CameraResponse:
    camera = await camera_service.get_camera(db, membership.tenant_id, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
    return await camera_service.update_camera(db, camera, data)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: uuid.UUID,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> None:
    camera = await camera_service.get_camera(db, membership.tenant_id, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")
    await camera_service.delete_camera(db, camera)


@router.post("/{camera_id}/stream-token", response_model=StreamTokenResponse)
async def get_stream_token(
    camera_id: uuid.UUID,
    membership: TenantMember = Depends(get_tenant_membership),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamTokenResponse:
    camera = await camera_service.get_camera(db, membership.tenant_id, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")

    stream_token = create_stream_token(user.id, membership.tenant_id, camera.stream_key)
    mjpeg_path = f"{settings.api_prefix}/streams/{camera.stream_key}/mjpeg?token={stream_token}"
    return StreamTokenResponse(
        camera_id=camera.id,
        stream_key=camera.stream_key,
        stream_token=stream_token,
        stream_url=f"{settings.public_api_url}{mjpeg_path}",
        mjpeg_url=f"{settings.public_api_url}{mjpeg_path}",
        expires_in_seconds=settings.stream_token_expire_minutes * 60,
    )
