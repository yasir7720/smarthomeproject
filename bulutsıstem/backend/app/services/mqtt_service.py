import asyncio
import json
import logging
import uuid

from aiomqtt import Client

from app.config import settings

logger = logging.getLogger(__name__)

_client_lock = asyncio.Lock()


def _client_kwargs() -> dict:
    return {
        "hostname": settings.mqtt_host,
        "port": settings.mqtt_port,
        "username": settings.mqtt_service_user,
        "password": settings.mqtt_service_password,
    }


async def publish(topic: str, payload: dict | str, qos: int = 1) -> None:
    message = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    async with _client_lock:
        async with Client(**_client_kwargs()) as client:
            await client.publish(topic, message, qos=qos)
    logger.info("MQTT publish %s -> %s", topic, message)


async def publish_raw(topic: str, message: str, qos: int = 1) -> None:
    async with _client_lock:
        async with Client(**_client_kwargs()) as client:
            await client.publish(topic, message, qos=qos)


async def listen(handler) -> None:
    patterns = [f"{settings.mqtt_topic_prefix}/#", "frigate/#"]
    while True:
        try:
            async with Client(**_client_kwargs()) as client:
                for pattern in patterns:
                    await client.subscribe(pattern)
                logger.info("MQTT dinleyici aktif: %s", ", ".join(patterns))
                async for message in client.messages:
                    topic = str(message.topic)
                    payload = message.payload.decode("utf-8", errors="replace")
                    await handler(topic, payload)
        except Exception as exc:
            logger.error("MQTT dinleyici hatası: %s — 5sn sonra yeniden", exc)
            await asyncio.sleep(5)


def extract_tenant_id_from_topic(topic: str) -> uuid.UUID | None:
    parts = topic.split("/")
    if len(parts) < 2 or parts[0] != settings.mqtt_topic_prefix:
        return None
    try:
        return uuid.UUID(parts[1])
    except ValueError:
        return None
