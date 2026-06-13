import asyncio
import base64
import contextlib
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, WebSocket, status

from app.config import settings

logger = logging.getLogger(__name__)


class TunnelManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, WebSocket] = {}
        self._queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    def is_connected(self, tenant_id: uuid.UUID) -> bool:
        return tenant_id in self._connections

    def tunnel_mjpeg_url(self, stream_key: str) -> str:
        return (
            f"{settings.public_api_url.rstrip('/')}{settings.api_prefix}"
            f"/edge/tunnel/mjpeg/{stream_key}?key={settings.tunnel_internal_key}"
        )

    async def register(self, tenant_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            existing = self._connections.get(tenant_id)
            if existing is not None:
                with contextlib.suppress(Exception):
                    await existing.close()
            self._connections[tenant_id] = websocket
        logger.info("Edge tünel bağlandı: tenant=%s", tenant_id)

    async def unregister(self, tenant_id: uuid.UUID) -> None:
        async with self._lock:
            self._connections.pop(tenant_id, None)

    async def handle_message(self, tenant_id: uuid.UUID, message: dict) -> None:
        request_id = message.get("request_id")
        if not request_id:
            return
        queue = self._queues.get(request_id)
        if queue is not None:
            await queue.put(message)

    async def proxy_stream(self, tenant_id: uuid.UUID, url: str) -> AsyncIterator[bytes]:
        websocket = self._connections.get(tenant_id)
        if websocket is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Edge agent tüneli bağlı değil",
            )

        request_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[request_id] = queue
        try:
            await websocket.send_json({"type": "stream_start", "request_id": request_id, "url": url})
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=60.0)
                except TimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Edge tünel zaman aşımı",
                    ) from None

                msg_type = message.get("type")
                if msg_type == "stream_chunk":
                    data = message.get("data", "")
                    if data:
                        yield base64.b64decode(data)
                elif msg_type == "stream_end":
                    error = message.get("error")
                    if error:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Edge tünel hatası: {error}",
                        )
                    break
        finally:
            self._queues.pop(request_id, None)


tunnel_manager = TunnelManager()
