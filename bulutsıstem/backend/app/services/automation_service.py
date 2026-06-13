import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mqtt_topics import master_control_topic, schedule_topic
from app.models.automation import AutomationRule, AutomationType
from app.schemas.automation import ScheduleRequest
from app.services import mqtt_service
from app.services.mqtt_service import extract_tenant_id_from_topic

logger = logging.getLogger(__name__)


async def trigger_home(tenant_id: uuid.UUID) -> None:
    from app.core.mqtt_topics import scenario_home_topic

    await mqtt_service.publish(scenario_home_topic(tenant_id), {"tetikleyici": "aktif"})
    await mqtt_service.publish_raw(master_control_topic(tenant_id), "1")


async def trigger_away(tenant_id: uuid.UUID) -> None:
    from app.core.mqtt_topics import scenario_away_topic

    await mqtt_service.publish(scenario_away_topic(tenant_id), {"tetikleyici": "aktif"})
    await mqtt_service.publish_raw(master_control_topic(tenant_id), "0")


async def set_schedule(tenant_id: uuid.UUID, data: ScheduleRequest) -> AutomationRule:
    payload = {"baslangic": data.baslangic, "bitis": data.bitis}
    await mqtt_service.publish(schedule_topic(tenant_id), payload)

    from app.database import async_session

    async with async_session() as db:
        result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.tenant_id == tenant_id,
                AutomationRule.rule_type == AutomationType.schedule,
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            rule = AutomationRule(
                tenant_id=tenant_id,
                name="Kişisel Zaman Penceresi",
                rule_type=AutomationType.schedule,
                config_json=json.dumps(payload, ensure_ascii=False),
            )
            db.add(rule)
        else:
            rule.config_json = json.dumps(payload, ensure_ascii=False)
        await db.commit()
        await db.refresh(rule)
        return rule


async def handle_mqtt_message(topic: str, payload: str) -> None:
    tenant_id = extract_tenant_id_from_topic(topic)
    if tenant_id is None:
        return

    if topic.endswith("/senaryo/evedonus"):
        logger.info("Senaryo eve dönüş tenant=%s", tenant_id)
        await mqtt_service.publish_raw(master_control_topic(tenant_id), "1")
    elif topic.endswith("/senaryo/evdencikis"):
        logger.info("Senaryo evden çıkış tenant=%s", tenant_id)
        await mqtt_service.publish_raw(master_control_topic(tenant_id), "0")


async def list_rules(db: AsyncSession, tenant_id: uuid.UUID) -> list[AutomationRule]:
    result = await db.execute(
        select(AutomationRule).where(AutomationRule.tenant_id == tenant_id).order_by(AutomationRule.created_at)
    )
    return list(result.scalars().all())
