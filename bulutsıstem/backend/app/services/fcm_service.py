import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.push_token import PushToken
from app.models.tenant import TenantMember

logger = logging.getLogger(__name__)

_fcm_ready = False


def _ensure_fcm() -> bool:
    global _fcm_ready
    if not settings.fcm_enabled:
        return False
    if _fcm_ready:
        return True
    cred_path = settings.fcm_credentials_path.strip()
    if not cred_path or not Path(cred_path).exists():
        logger.warning("FCM etkin ama kimlik dosyası yok: %s", cred_path or "(boş)")
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        _fcm_ready = True
        return True
    except Exception as exc:
        logger.error("FCM başlatılamadı: %s", exc)
        return False


async def _tenant_tokens(db: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(PushToken.token)
        .join(TenantMember, TenantMember.user_id == PushToken.user_id)
        .where(TenantMember.tenant_id == tenant_id)
    )
    return [row[0] for row in result.all()]


async def notify_person_detected(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    camera_name: str,
    count: int,
) -> int:
    if not _ensure_fcm():
        return 0

    tokens = await _tenant_tokens(db, tenant_id)
    if not tokens:
        return 0

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Güvenlik Alarmı",
                body=f"{camera_name}: {count} kişi algılandı",
            ),
            data={
                "type": "person_detected",
                "camera_name": camera_name,
                "count": str(count),
                "tenant_id": str(tenant_id),
            },
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        logger.info("FCM gönderildi: %d başarılı / %d token", response.success_count, len(tokens))
        return response.success_count
    except Exception as exc:
        logger.error("FCM gönderim hatası: %s", exc)
        return 0
