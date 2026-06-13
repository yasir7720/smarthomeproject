from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_membership, require_role
from app.database import get_db
from app.models.tenant import TenantMember, TenantRole
from app.schemas.automation import AutomationRuleResponse, ScenarioResponse, ScheduleRequest
from app.services import automation_service

router = APIRouter(prefix="/tenants/{tenant_id}/automations", tags=["Otomasyon"])


@router.get("", response_model=list[AutomationRuleResponse])
async def list_automations(
    membership: TenantMember = Depends(get_tenant_membership),
    db: AsyncSession = Depends(get_db),
) -> list[AutomationRuleResponse]:
    return await automation_service.list_rules(db, membership.tenant_id)


@router.post("/home", response_model=ScenarioResponse)
async def scenario_home(
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
) -> ScenarioResponse:
    await automation_service.trigger_home(membership.tenant_id)
    return ScenarioResponse(message="Eve dönüş senaryosu tetiklendi", tenant_id=membership.tenant_id)


@router.post("/away", response_model=ScenarioResponse)
async def scenario_away(
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
) -> ScenarioResponse:
    await automation_service.trigger_away(membership.tenant_id)
    return ScenarioResponse(message="Evden çıkış senaryosu tetiklendi", tenant_id=membership.tenant_id)


@router.post("/schedule", response_model=AutomationRuleResponse)
async def scenario_schedule(
    data: ScheduleRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
) -> AutomationRuleResponse:
    rule = await automation_service.set_schedule(membership.tenant_id, data)
    return rule
