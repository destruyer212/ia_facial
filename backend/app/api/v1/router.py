from fastapi import APIRouter

from app.api.v1.endpoints import attendance, faces, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(faces.router, prefix="/faces", tags=["faces"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
