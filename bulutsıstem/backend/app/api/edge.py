from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_by_edge_key, get_tenant_membership, require_role
from app.config import settings
from app.database import async_session, get_db
from app.models.camera import CameraSourceKind
from app.models.tenant import Tenant, TenantMember, TenantRole
from app.schemas.camera import CameraResponse
from app.schemas.edge import (
    EdgeHeartbeatRequest,
    EdgeHeartbeatResponse,
    EdgeInfoResponse,
    EdgeIpWebcamRequest,
    EdgeTunnelStatusResponse,
    IpWebcamCreateRequest,
)
from app.services import camera_service, stream_service
from app.services.tunnel_service import tunnel_manager

router = APIRouter(tags=["Edge Agent"])


@router.get("/tenants/{tenant_id}/edge/info", response_model=EdgeInfoResponse)
async def edge_info(membership: TenantMember = Depends(get_tenant_membership)) -> EdgeInfoResponse:
    tenant = membership.tenant
    return EdgeInfoResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        edge_agent_key=tenant.edge_agent_key,
    )


@router.post("/tenants/{tenant_id}/cameras/ip-webcam", response_model=CameraResponse, tags=["Kameralar"])
async def add_ip_webcam_camera(
    data: IpWebcamCreateRequest,
    membership: TenantMember = Depends(require_role(TenantRole.owner, TenantRole.admin)),
    db: AsyncSession = Depends(get_db),
) -> CameraResponse:
    return await camera_service.create_ip_webcam_camera(db, membership.tenant_id, data)


@router.post("/edge/heartbeat", response_model=EdgeHeartbeatResponse)
async def edge_heartbeat(
    data: EdgeHeartbeatRequest,
    tenant: Tenant = Depends(get_tenant_by_edge_key),
    db: AsyncSession = Depends(get_db),
) -> EdgeHeartbeatResponse:
    tenant.edge_agent_last_seen = datetime.now(UTC)
    await db.commit()
    await db.refresh(tenant)
    return EdgeHeartbeatResponse(
        tenant_id=tenant.id,
        status="ok",
        last_seen=tenant.edge_agent_last_seen,
    )


@router.post("/edge/cameras/ip-webcam", response_model=CameraResponse)
async def edge_register_ip_webcam(
    data: EdgeIpWebcamRequest,
    tenant: Tenant = Depends(get_tenant_by_edge_key),
    db: AsyncSession = Depends(get_db),
) -> CameraResponse:
    return await camera_service.create_ip_webcam_camera(
        db, tenant.id, data, source_kind=CameraSourceKind.edge_agent.value
    )


@router.get("/tenants/{tenant_id}/edge/tunnel/status", response_model=EdgeTunnelStatusResponse)
async def tunnel_status(
    membership: TenantMember = Depends(get_tenant_membership),
) -> EdgeTunnelStatusResponse:
    connected = tunnel_manager.is_connected(membership.tenant_id)
    return EdgeTunnelStatusResponse(
        tenant_id=membership.tenant_id,
        connected=connected,
        message="Edge agent tüneli aktif" if connected else "Edge agent bağlı değil",
    )


@router.websocket("/edge/tunnel/ws")
async def edge_tunnel_ws(websocket: WebSocket) -> None:
    agent_key = websocket.headers.get("x-agent-key")
    if not agent_key:
        await websocket.close(code=4401, reason="X-Agent-Key gerekli")
        return

    async with async_session() as db:
        result = await db.execute(select(Tenant).where(Tenant.edge_agent_key == agent_key))
        tenant = result.scalar_one_or_none()

    if tenant is None:
        await websocket.close(code=4401, reason="Geçersiz edge agent anahtarı")
        return

    await websocket.accept()
    await tunnel_manager.register(tenant.id, websocket)
    async with async_session() as db:
        await stream_service.sync_tenant_edge_cameras(db, tenant.id)

    try:
        while True:
            message = await websocket.receive_json()
            await tunnel_manager.handle_message(tenant.id, message)
    except WebSocketDisconnect:
        pass
    finally:
        await tunnel_manager.unregister(tenant.id)


@router.get("/edge/tunnel/mjpeg/{stream_key}")
async def edge_tunnel_mjpeg(
    stream_key: str,
    key: str = Query(..., description="Dahili tünel anahtarı"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if key != settings.tunnel_internal_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz tünel anahtarı")

    camera = await camera_service.get_camera_by_stream_key(db, stream_key)
    if camera is None or camera.source_kind != CameraSourceKind.edge_agent.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge kamera bulunamadı")

    async def relay():
        async for chunk in tunnel_manager.proxy_stream(camera.tenant_id, camera.stream_url):
            yield chunk

    return StreamingResponse(
        relay(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
