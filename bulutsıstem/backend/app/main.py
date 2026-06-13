import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database import async_session, init_db
from app.services import (
    automation_service,
    detection_service,
    frigate_config_service,
    mqtt_provision_service,
    mqtt_service,
    stream_service,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_mqtt_task: asyncio.Task | None = None


async def _mqtt_handler(topic: str, payload: str) -> None:
    if topic.startswith("frigate/") and topic.endswith("/person"):
        await detection_service.handle_frigate_person_topic(topic, payload)
    await automation_service.handle_mqtt_message(topic, payload)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _mqtt_task
    await init_db()
    async with async_session() as db:
        await mqtt_provision_service.sync_broker_credentials(db)
        await stream_service.sync_all_cameras(db)
        await frigate_config_service.sync_config(db)
    _mqtt_task = asyncio.create_task(mqtt_service.listen(_mqtt_handler))
    logger.info("BulutSistem başlatıldı")
    yield
    if _mqtt_task:
        _mqtt_task.cancel()
        with suppress(asyncio.CancelledError):
            await _mqtt_task


app = FastAPI(
    title=settings.app_name,
    description="Çok kullanıcılı akıllı ev ve kamera platformu",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "phase": "security-complete",
        "components": [
            "api", "postgres", "go2rtc", "frigate", "mqtt_auth", "devices",
            "automations", "ip_webcam", "edge_tunnel", "person_detection",
            "fcm_push", "plan_limits", "members",
        ],
    }
