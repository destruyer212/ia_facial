from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    admin,
    attendance,
    auth,
    employees,
    faces,
    health,
    mobile,
    registration_tokens,
    schedules,
)
from app.core.auth import get_current_user

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
protected = [Depends(get_current_user)]
api_router.include_router(faces.router, prefix="/faces", tags=["faces"], dependencies=protected)
api_router.include_router(employees.router, prefix="/employees", tags=["employees"], dependencies=protected)
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"], dependencies=protected)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=protected)
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"], dependencies=protected)
api_router.include_router(registration_tokens.router, prefix="/registration-tokens", tags=["registration-tokens"])
api_router.include_router(mobile.router, prefix="/mobile", tags=["mobile"])
