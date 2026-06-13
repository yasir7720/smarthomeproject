import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_stream_token
from app.database import get_db
from app.services import camera_service, stream_service

router = APIRouter(prefix="/streams", tags=["Yayın"])


@router.get("/{stream_key}/mjpeg")
async def watch_mjpeg(
    stream_key: str,
    token: str = Query(..., description="stream-token endpoint'inden alınan kısa ömürlü token"),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_stream_token(token)
    if payload is None or payload["stream_key"] != stream_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz stream token")

    camera = await camera_service.get_camera_by_stream_key(db, stream_key)
    if camera is None or camera.tenant_id != payload["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kamera bulunamadı")

    upstream = stream_service.mjpeg_proxy_url(stream_key)

    async def relay():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", upstream) as response:
                if response.status_code != 200:
                    yield b""
                    return
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        relay(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
