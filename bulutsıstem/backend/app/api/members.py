import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_membership, require_role
from app.database import get_db
from app.models.tenant import TenantMember, TenantRole
from app.models.user import User
from app.schemas.member import MemberInviteRequest, MemberResponse

router = APIRouter(prefix="/tenants/{tenant_id}/members", tags=["Üyeler"])


@router.get("", response_model=list[MemberResponse])
async def list_members(
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    result = await db.execute(
        select(TenantMember, User)
        .join(User, User.id == TenantMember.user_id)
        .where(TenantMember.tenant_id == membership.tenant_id)
    )
    rows = result.all()
    return [
        MemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: MemberInviteRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    user_result = await db.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı. Önce kayıt olması gerekir.",
        )

    existing = await db.execute(
        select(TenantMember).where(
            TenantMember.tenant_id == membership.tenant_id,
            TenantMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Kullanıcı zaten bu evde")

    new_member = TenantMember(tenant_id=membership.tenant_id, user_id=user.id, role=data.role)
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=new_member.role,
        joined_at=new_member.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID,
    membership: TenantMember = Depends(require_role(TenantRole.owner)),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == membership.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendinizi silemezsiniz")
    result = await db.execute(
        select(TenantMember).where(
            TenantMember.tenant_id == membership.tenant_id,
            TenantMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Üye bulunamadı")
    await db.delete(member)
    await db.commit()
