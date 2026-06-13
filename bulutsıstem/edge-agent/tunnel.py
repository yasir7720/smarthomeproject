from __future__ import annotations

import asyncio
import base64
import json
import logging
from urllib.parse import urlparse, urlunparse

import httpx
import websockets

logger = logging.getLogger(__name__)


def _ws_url(api_url: str) -> str:
    parsed = urlparse(api_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/") + "/edge/tunnel/ws"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


async def _stream_local_camera(
    websocket,
    request_id: str,
    url: str,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "stream_end",
                                "request_id": request_id,
                                "error": f"HTTP {response.status_code}",
                            }
                        )
                    )
                    return
                async for chunk in response.aiter_bytes():
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "stream_chunk",
                                "request_id": request_id,
                                "data": base64.b64encode(chunk).decode("ascii"),
                            }
                        )
                    )
        await websocket.send(json.dumps({"type": "stream_end", "request_id": request_id}))
    except Exception as exc:
        await websocket.send(
            json.dumps({"type": "stream_end", "request_id": request_id, "error": str(exc)})
        )


async def run_tunnel(api_url: str, agent_key: str) -> None:
    ws_url = _ws_url(api_url)
    headers = {"X-Agent-Key": agent_key}
    logger.info("Edge tünel bağlanıyor: %s", ws_url)

    while True:
        try:
            async with websockets.connect(ws_url, additional_headers=headers, ping_interval=20) as websocket:
                logger.info("Edge tünel bağlantısı kuruldu")
                async for raw in websocket:
                    message = json.loads(raw)
                    if message.get("type") != "stream_start":
                        continue
                    request_id = message["request_id"]
                    url = message["url"]
                    asyncio.create_task(_stream_local_camera(websocket, request_id, url))
        except Exception as exc:
            logger.warning("Edge tünel hatası: %s — 3sn sonra yeniden", exc)
            await asyncio.sleep(3)
