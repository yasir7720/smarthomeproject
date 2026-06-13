import logging
import os
import subprocess
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


def _run_passwd(users: list[tuple[str, str]], passwd_path: Path) -> None:
    passwd_path.parent.mkdir(parents=True, exist_ok=True)
    for index, (username, password) in enumerate(users):
        command = ["mosquitto_passwd"]
        if index == 0:
            command.extend(["-c", "-b"])
        else:
            command.append("-b")
        command.extend([str(passwd_path), username, password])
        subprocess.run(command, check=True, capture_output=True)


def _build_acl(tenants: list[Tenant]) -> str:
    prefix = settings.mqtt_topic_prefix
    lines = [
        f"user {settings.mqtt_service_user}",
        "topic readwrite #",
        "",
        f"user {settings.mqtt_frigate_user}",
        "topic readwrite frigate/#",
        "",
    ]
    for tenant in tenants:
        topic_root = f"{prefix}/{tenant.id}"
        lines.extend(
            [
                f"user {tenant.mqtt_username}",
                f"topic read {topic_root}/#",
                f"topic write {topic_root}/ev/#",
                f"topic write {topic_root}/senaryo/#",
                f"topic write {topic_root}/hydra/#",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


async def sync_broker_credentials(db: AsyncSession) -> tuple[bool, str]:
    passwd_path = Path(settings.mqtt_passwd_path)
    acl_path = Path(settings.mqtt_acl_path)

    result = await db.execute(select(Tenant).order_by(Tenant.created_at))
    tenants = list(result.scalars().all())

    users = [
        (settings.mqtt_service_user, settings.mqtt_service_password),
        (settings.mqtt_frigate_user, settings.mqtt_frigate_password),
    ]
    users.extend((tenant.mqtt_username, tenant.mqtt_password) for tenant in tenants)

    try:
        _run_passwd(users, passwd_path)
        acl_path.write_text(_build_acl(tenants), encoding="utf-8")
        os.chmod(passwd_path, 0o644)
        os.chmod(acl_path, 0o644)
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.error("MQTT kimlik dosyası yazılamadı: %s", exc)
        return False, f"MQTT kimlik dosyası yazılamadı: {exc}"

    logger.info("MQTT kimlik dosyası güncellendi (%d tenant)", len(tenants))
    return True, f"MQTT kimlik dosyası güncellendi ({len(tenants)} tenant)"
