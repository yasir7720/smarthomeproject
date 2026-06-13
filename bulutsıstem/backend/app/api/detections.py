from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_membership
from app.database import get_db
from app.models.tenant import TenantMember
from app.schemas.detection import DetectionEventResponse
from app.services import detection_service

router = APIRouter(prefix="/tenants/{tenant_id}/detections", tags=["Algılama"])


@router.get("", response_model=list[DetectionEventResponse])
async def list_detections(
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> list[DetectionEventResponse]:
    return await detection_service.list_events(db, membership.tenant_id)
