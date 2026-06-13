import uuid

from app.config import settings


def tenant_prefix(tenant_id: uuid.UUID) -> str:
    return f"{settings.mqtt_topic_prefix}/{tenant_id}"


def device_topic(tenant_id: uuid.UUID, room: str, device_slug: str) -> str:
    return f"{tenant_prefix(tenant_id)}/ev/{room}/{device_slug}"


def scenario_home_topic(tenant_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/senaryo/evedonus"


def scenario_away_topic(tenant_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/senaryo/evdencikis"


def schedule_topic(tenant_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/otomasyon/zaman"


def master_control_topic(tenant_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/hydra/master_kontrol"


def camera_person_topic(tenant_id: uuid.UUID, camera_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/cameras/{camera_id}/person"


def camera_person_wildcard(tenant_id: uuid.UUID) -> str:
    return f"{tenant_prefix(tenant_id)}/cameras/+/person"
