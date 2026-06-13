from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.push_token import PushToken
from app.core.security import (
    create_access_token,
    generate_edge_agent_key,
    generate_mqtt_password,
    generate_tenant_slug,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.tenant import Tenant, TenantMember, TenantRole
from app.models.user import User
from app.schemas.auth import LoginRequest, PushTokenRequest, PushTokenResponse, RegisterRequest, TokenResponse, UserResponse
from app.services import device_service, mqtt_provision_service

router = APIRouter(prefix="/auth", tags=["Kimlik"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")

    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )
    slug = generate_tenant_slug(data.email)
    tenant = Tenant(
        name=data.tenant_name,
        slug=slug,
        mqtt_username=f"tenant_{slug}",
        mqtt_password=generate_mqtt_password(),
        edge_agent_key=generate_edge_agent_key(),
    )
    membership = TenantMember(tenant=tenant, user=user, role=TenantRole.owner)

    db.add_all([user, tenant, membership])
    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)

    await device_service.seed_default_devices(db, tenant.id)
    await mqtt_provision_service.sync_broker_credentials(db)

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya şifre hatalı")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hesap devre dışı")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/push-token", response_model=PushTokenResponse)
async def register_push_token(
    data: PushTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushTokenResponse:
    result = await db.execute(select(PushToken).where(PushToken.token == data.token))
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(PushToken(user_id=user.id, token=data.token, platform=data.platform))
    else:
        existing.user_id = user.id
        existing.platform = data.platform
    await db.commit()
    return PushTokenResponse(registered=True, message="Push token kaydedildi")
