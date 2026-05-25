from datetime import UTC, datetime, time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.core.config import settings
from app.schemas.attendance import (
    AttendanceEventCreate,
    AttendanceEventListResponse,
    AttendanceEventResponse,
    ExitAttemptRequest,
    ExitAttemptResponse,
    ExitPolicyResponse,
    FaceExitAttemptResponse,
    IncidentListResponse,
)
from app.services.attendance_service import AttendanceService
from app.services.attendance_event_store import LocalAttendanceEventStore
from app.services.embedding_store import LocalEmbeddingStore
from app.services.face_ai_service import FaceAIService
from app.services.incident_store import LocalIncidentStore
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
attendance_service = AttendanceService()
incident_store = LocalIncidentStore()
attendance_event_store = LocalAttendanceEventStore()
face_ai_service = FaceAIService()
embedding_store = LocalEmbeddingStore()


@router.get("/policy", response_model=ExitPolicyResponse)
def get_attendance_policy() -> ExitPolicyResponse:
    return attendance_service.get_policy()


@router.post("/exit-attempts", response_model=ExitAttemptResponse)
def evaluate_exit_attempt(payload: ExitAttemptRequest) -> ExitAttemptResponse:
    return attendance_service.evaluate_exit_attempt(
        person_id=payload.person_id,
        employee_name=payload.employee_name,
        attempted_at=payload.attempted_at,
        scheduled_exit_time=payload.scheduled_exit_time,
        tolerance_minutes=payload.tolerance_minutes,
        reason=payload.reason,
        source=payload.source,
    )


@router.post("/events", response_model=AttendanceEventResponse)
def create_attendance_event(payload: AttendanceEventCreate) -> AttendanceEventResponse:
    event = attendance_event_store.create(payload)
    message = (
        "Evento duplicado ignorado para asistencia."
        if event.duplicate
        else "Asistencia registrada."
    )
    return AttendanceEventResponse(event=event, message=message)


@router.get("/events", response_model=AttendanceEventListResponse)
def list_attendance_events(
    person_id: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> AttendanceEventListResponse:
    return AttendanceEventListResponse(
        events=attendance_event_store.list(
            person_id=person_id,
            device_id=device_id,
            limit=limit,
        )
    )


@router.post("/exit-attempts/with-face", response_model=FaceExitAttemptResponse)
async def evaluate_exit_attempt_with_face(
    file: UploadFile = File(...),
    attempted_at: str | None = Form(default=None),
    scheduled_exit_time: str | None = Form(default=None),
    tolerance_minutes: int | None = Form(default=None, ge=0, le=180),
    reason: str | None = Form(default=None),
    source: str = Form(default="android"),
) -> FaceExitAttemptResponse:
    image_path = await _persist_upload(file)
    try:
        embedding = face_ai_service.create_embedding(image_path)
        match = embedding_store.find_best_match(
            embedding=embedding,
            threshold=settings.face_match_threshold,
            model=settings.deepface_model,
        )
        if match is None:
            return FaceExitAttemptResponse(
                face_matched=False,
                candidate=None,
                attendance=None,
                message="Rostro no reconocido. No se puede validar salida.",
            )

        attendance = attendance_service.evaluate_exit_attempt(
            person_id=match.person_id,
            employee_name=match.name,
            attempted_at=parse_optional_datetime(attempted_at),
            scheduled_exit_time=parse_optional_time(scheduled_exit_time),
            tolerance_minutes=tolerance_minutes,
            reason=reason,
            source=source,
            evidence_ref=f"{source}:{file.filename or 'uploaded-image'}",
        )
        return FaceExitAttemptResponse(
            face_matched=True,
            candidate=match,
            attendance=attendance,
            message=attendance.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando salida con rostro: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.get("/incidents", response_model=IncidentListResponse)
def list_incidents(
    person_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> IncidentListResponse:
    return IncidentListResponse(incidents=incident_store.list(person_id=person_id, limit=limit))


async def _persist_upload(file: UploadFile) -> Path:
    try:
        return await save_upload_to_temp_file(file, max_mb=settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_optional_time(value: str | None) -> time | None:
    if not value:
        return None
    return time.fromisoformat(value)
