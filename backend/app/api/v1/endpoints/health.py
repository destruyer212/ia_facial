from fastapi import APIRouter

from app.core.config import settings
from app.services.supabase_db import test_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "face_engine": settings.face_engine,
        "face_model": settings.active_face_model,
    }


@router.get("/health/ai")
def ai_health_check() -> dict[str, str | bool]:
    checks: dict[str, str | bool] = {
        "face_engine": settings.face_engine,
        "face_model": settings.active_face_model,
        "mediapipe": False,
        "insightface": False,
    }
    try:
        import mediapipe as mp

        if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
            checks["mediapipe"] = True
        else:
            checks["mediapipe_message"] = (
                "mediapipe sin API solutions; fija mediapipe==0.10.21 en requirements.txt"
            )
    except ImportError:
        checks["mediapipe_message"] = "mediapipe no instalado (pip install mediapipe)"

    if settings.face_engine.lower() == "insightface":
        try:
            from insightface.app import FaceAnalysis  # noqa: F401

            checks["insightface"] = True
        except ImportError:
            checks["insightface_message"] = "insightface no instalado (pip install insightface onnxruntime)"
    else:
        checks["insightface"] = "skipped"

    checks["status"] = "ok" if checks["mediapipe"] else "degraded"
    return checks


@router.get("/health/db")
def database_health_check() -> dict[str, str | bool]:
    if settings.storage_backend.lower() != "supabase":
        return {
            "status": "skipped",
            "storage_backend": settings.storage_backend,
            "connected": False,
            "message": "STORAGE_BACKEND no es supabase; no se prueba la base de datos.",
        }

    connected, message = test_connection()
    return {
        "status": "ok" if connected else "error",
        "storage_backend": settings.storage_backend,
        "connected": connected,
        "message": message,
    }

