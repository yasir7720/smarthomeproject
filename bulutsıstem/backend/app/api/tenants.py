import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_tenant_membership
from app.config import settings
from app.core.mqtt_topics import tenant_prefix
from app.database import get_db
from app.models.tenant import TenantMember
from app.models.user import User
from app.schemas.tenant import MqttCredentialsResponse, TenantResponse

router = APIRouter(prefix="/tenants", tags=["Evler"])


@router.get("", response_model=list[TenantResponse])
async def list_my_tenants(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TenantResponse]:
    result = await db.execute(
        select(TenantMember)
        .options(selectinload(TenantMember.tenant))
        .where(TenantMember.user_id == user.id)
    )
    memberships = result.scalars().all()
    return [
        TenantResponse(
            id=m.tenant.id,
            name=m.tenant.name,
            slug=m.tenant.slug,
            plan=m.tenant.plan,
            status=m.tenant.status,
            role=m.role,
            created_at=m.tenant.created_at,
        )
        for m in memberships
    ]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(membership: TenantMember = Depends(get_tenant_membership)) -> TenantResponse:
    tenant = membership.tenant
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        status=tenant.status,
        role=membership.role,
        created_at=tenant.created_at,
    )


@router.get("/{tenant_id}/mqtt-credentials", response_model=MqttCredentialsResponse)
async def mqtt_credentials(membership: TenantMember = Depends(get_tenant_membership)) -> MqttCredentialsResponse:
    tenant = membership.tenant
    return MqttCredentialsResponse(
        host=settings.public_mqtt_host,
        port=settings.public_mqtt_port,
        username=tenant.mqtt_username,
        password=tenant.mqtt_password,
        topic_prefix=tenant_prefix(tenant.id),
    )
