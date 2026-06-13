from fastapi import APIRouter

from app.api import auth, automations, cameras, detections, devices, edge, members, streams, tenants

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(members.router)
api_router.include_router(cameras.router)
api_router.include_router(edge.router)
api_router.include_router(devices.router)
api_router.include_router(automations.router)
api_router.include_router(detections.router)
api_router.include_router(streams.router)
