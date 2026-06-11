from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    attendance,
    employees,
    faces,
    health,
    mobile,
    registration_tokens,
    schedules,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(faces.router, prefix="/faces", tags=["faces"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(registration_tokens.router, prefix="/registration-tokens", tags=["registration-tokens"])
api_router.include_router(mobile.router, prefix="/mobile", tags=["mobile"])
