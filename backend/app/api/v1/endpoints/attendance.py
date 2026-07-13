from datetime import UTC, date, datetime, time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.core.config import settings
from app.schemas.attendance import (
    AttendanceEventCreate,
    AttendanceEventListResponse,
    AttendanceEventResponse,
    AttendanceEventDeleteResponse,
    AttendanceEventUpdate,
    AttendanceEventUpdateResponse,
    ExitAttemptRequest,
    ExitAttemptResponse,
    ExitPolicyResponse,
    FaceExitAttemptResponse,
    IncidentListResponse,
    SuggestEventResponse,
)
from app.services.attendance_service import AttendanceService
from app.services.attendance_workflow_service import AttendanceWorkflowService
from app.services.attendance_event_store import (
    build_attendance_summary,
    get_attendance_event_store,
)
from app.services.embedding_store import get_embedding_store
from app.services.face_ai_service import FaceAIService
from app.services.face_match_service import match_face_from_image
from app.services.incident_store import get_incident_store
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
incident_store = get_incident_store()
attendance_service = AttendanceService(incident_store=incident_store)
attendance_event_store = get_attendance_event_store()
attendance_workflow_service = AttendanceWorkflowService(event_store=attendance_event_store)
face_ai_service = FaceAIService()
embedding_store = get_embedding_store()


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
    try:
        event = attendance_event_store.create(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando asistencia: {exc}",
        ) from exc
    label = payload.employee_name or payload.person_id
    if event.duplicate:
        if event.event_type == "check_in":
            message = f"{label}: ya registraste entrada hoy. Si saliste, marca salida."
        elif event.event_type == "check_out":
            message = f"{label}: ya registraste salida hoy."
        else:
            message = f"{label}: evento duplicado ignorado para asistencia."
    elif event.event_type == "check_in":
        message = f"{label}: entrada registrada correctamente."
    elif event.event_type == "check_out":
        message = f"{label}: salida registrada correctamente."
    else:
        message = f"{label}: asistencia registrada."
    return AttendanceEventResponse(event=event, message=message)


@router.get("/suggest-event", response_model=SuggestEventResponse)
def suggest_attendance_event(
    person_id: str = Query(..., min_length=1),
) -> SuggestEventResponse:
    return attendance_workflow_service.suggest_next_event(person_id=person_id)


@router.get("/events", response_model=AttendanceEventListResponse)
def list_attendance_events(
    person_id: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> AttendanceEventListResponse:
    if event_type and event_type not in {"check_in", "check_out"}:
        raise HTTPException(status_code=400, detail="event_type debe ser check_in o check_out.")
    events = attendance_event_store.list(
        person_id=person_id,
        device_id=device_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return AttendanceEventListResponse(
        events=events,
        summary=build_attendance_summary(events),
    )


@router.get("/events/{event_id}", response_model=AttendanceEventResponse)
def get_attendance_event(event_id: str) -> AttendanceEventResponse:
    event = attendance_event_store.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"No existe evento '{event_id}'.")
    return AttendanceEventResponse(event=event, message="Evento encontrado.")


@router.patch("/events/{event_id}", response_model=AttendanceEventUpdateResponse)
def update_attendance_event(
    event_id: str,
    payload: AttendanceEventUpdate,
) -> AttendanceEventUpdateResponse:
    try:
        event = attendance_event_store.update(event_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AttendanceEventUpdateResponse(
        event=event,
        message="Marca de asistencia corregida correctamente.",
    )


@router.delete("/events/{event_id}", response_model=AttendanceEventDeleteResponse)
def delete_attendance_event(event_id: str) -> AttendanceEventDeleteResponse:
    existing = attendance_event_store.get(event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No existe evento '{event_id}'.")
    try:
        attendance_event_store.delete(event_id, target=existing)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    label = existing.employee_name or existing.person_id
    tipo = "salida" if existing.event_type == "check_out" else "entrada"
    return AttendanceEventDeleteResponse(
        event_id=event_id,
        message=f"{label}: marca de {tipo} eliminada.",
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
        identity = match_face_from_image(image_path)
        match = identity.candidate
        if not identity.matched or match is None:
            return FaceExitAttemptResponse(
                face_matched=False,
                candidate=identity.near_miss,
                attendance=None,
                message=identity.message or "Rostro no reconocido. No se puede validar salida.",
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
