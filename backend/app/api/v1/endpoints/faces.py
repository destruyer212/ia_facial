from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.face import (
    AnalyzeFaceResponse,
    EmbeddingResponse,
    FaceDetectionResponse,
    IdentifyFaceResponse,
    LivenessChallengeResponse,
    LivenessVerifyResponse,
    RegisteredFacesResponse,
    RegisterFaceProfileResponse,
    RegisterFaceResponse,
    StorageStatusResponse,
    DeleteEmployeeResponse,
    DeleteEmployeeStats,
    UpdateEmployeePhotoResponse,
    UpdateEmployeeRequest,
    UpdateEmployeeResponse,
)
from app.services.attendance_event_store import get_attendance_event_store
from app.services.employee_catalog_service import get_employee_catalog_service
from app.services.embedding_store import get_embedding_store, sanitize_person_id
from app.services.incident_store import get_incident_store
from app.services.liveness_service import LivenessService
from app.services.supabase_db import get_conn, resolve_org_id, save_face_asset
from app.services.face_ai_service import FaceAIService
from app.services.face_match_service import match_face_from_image
from app.services.opencv_service import OpenCVService
from app.services.r2_storage_service import R2StorageService
from app.services.schedule_service import get_schedule_service
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
opencv_service = OpenCVService()
face_ai_service = FaceAIService()
_liveness_service: LivenessService | None = None
embedding_store = get_embedding_store()


def get_liveness_service() -> LivenessService:
    global _liveness_service
    if _liveness_service is None:
        _liveness_service = LivenessService(face_ai=face_ai_service, opencv=opencv_service)
    return _liveness_service
employee_catalog_service = get_employee_catalog_service()
attendance_event_store = get_attendance_event_store()
incident_store = get_incident_store()
r2_storage = R2StorageService() if settings.r2_enabled else None


@router.post("/detect", response_model=FaceDetectionResponse)
async def detect_faces(file: UploadFile = File(...)) -> FaceDetectionResponse:
    image_path = await _persist_upload(file)
    try:
        return opencv_service.detect_faces(image_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        remove_file(image_path)


@router.post("/analyze", response_model=AnalyzeFaceResponse)
async def analyze_face(file: UploadFile = File(...)) -> AnalyzeFaceResponse:
    image_path = await _persist_upload(file)
    try:
        analysis = face_ai_service.analyze_image(image_path)
        return AnalyzeFaceResponse(**analysis)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando DeepFace: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.post("/embedding", response_model=EmbeddingResponse)
async def create_embedding(file: UploadFile = File(...)) -> EmbeddingResponse:
    image_path = await _persist_upload(file)
    try:
        embedding = face_ai_service.create_embedding(image_path)
        return EmbeddingResponse(
            model=settings.active_face_model,
            vector_size=len(embedding),
            embedding_preview=[round(float(value), 6) for value in embedding[:8]],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando embedding facial: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.post("/register", response_model=RegisterFaceResponse)
async def register_face(
    person_id: str = Form(...),
    name: str = Form(...),
    email: str | None = Form(None),
    file: UploadFile = File(...),
) -> RegisterFaceResponse:
    image_path = await _persist_upload(file)
    content_type = file.content_type or "image/jpeg"
    try:
        stored, image_url, r2_saved, image_key, storage_message = await _upsert_face_from_image(
            person_id=person_id,
            name=name,
            email=email.strip() if email else None,
            image_path=image_path,
            content_type=content_type,
        )
        return RegisterFaceResponse(
            person_id=stored.person_id,
            name=stored.name,
            model=stored.model,
            total_embeddings=embedding_store.count(),
            r2_saved=r2_saved,
            image_key=image_key,
            image_url=image_url,
            storage_message=storage_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando rostro: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.post("/register-profile", response_model=RegisterFaceProfileResponse)
async def register_face_profile(
    area_code: str = Form(...),
    position_code: str = Form(...),
    shift_code: str | None = Form(None),
    name: str = Form(...),
    email: str | None = Form(None),
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    with_glasses: UploadFile | None = File(None),
    without_glasses: UploadFile | None = File(None),
) -> RegisterFaceProfileResponse:
    if shift_code:
        shift = get_schedule_service().get_shift(shift_code)
        if shift is None or not shift.is_active:
            raise HTTPException(status_code=400, detail=f"Turno '{shift_code}' no existe o esta inactivo.")
    try:
        allocated = employee_catalog_service.allocate_employee_code(area_code, position_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    person_id = allocated.employee_code
    uploads: dict[str, UploadFile] = {
        "front": front,
        "left": left,
        "right": right,
    }
    if with_glasses is not None and with_glasses.filename:
        uploads["with_glasses"] = with_glasses
    if without_glasses is not None and without_glasses.filename:
        uploads["without_glasses"] = without_glasses

    temp_paths: list[Path] = []
    poses_saved: list[str] = []
    image_url: str | None = None
    r2_saved = False
    storage_messages: list[str] = []

    try:
        for pose_type, upload in uploads.items():
            image_path = await _persist_upload(upload)
            temp_paths.append(image_path)
            content_type = upload.content_type or "image/jpeg"
            stored, pose_url, pose_r2, _, pose_msg = await _upsert_face_from_image(
                person_id=person_id,
                name=name,
                email=email.strip() if email else None,
                image_path=image_path,
                content_type=content_type,
                pose_type=pose_type,
                employee_code=allocated.employee_code,
                area_code=allocated.area_code,
                position_code=allocated.position_code,
                area_name=allocated.area_name,
                position_name=allocated.position_name,
            )
            poses_saved.append(pose_type)
            if pose_type == "front":
                image_url = pose_url
            if pose_r2:
                r2_saved = True
            if pose_msg:
                storage_messages.append(pose_msg)

        total = embedding_store.count_person_embeddings(person_id)
        if shift_code:
            get_schedule_service().assign_shift(person_id, shift_code)
        return RegisterFaceProfileResponse(
            person_id=stored.person_id,
            name=stored.name,
            model=stored.model,
            poses_saved=poses_saved,
            total_embeddings=embedding_store.count(),
            embedding_count=total,
            r2_saved=r2_saved,
            image_url=image_url,
            storage_message="; ".join(storage_messages) if storage_messages else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando perfil facial: {exc}",
        ) from exc
    finally:
        for path in temp_paths:
            remove_file(path)


@router.get("/liveness/challenge", response_model=LivenessChallengeResponse)
def get_liveness_challenge() -> LivenessChallengeResponse:
    return get_liveness_service().create_challenge()


@router.post("/liveness/verify", response_model=LivenessVerifyResponse)
async def verify_liveness(
    challenge_id: str | None = Form(None),
    person_id: str | None = Form(None),
    step_front: UploadFile = File(...),
    step_movement: UploadFile = File(...),
    step_blink: UploadFile = File(...),
    step_smile: UploadFile | None = File(None),
) -> LivenessVerifyResponse:
    uploads: dict[str, UploadFile] = {
        "front": step_front,
        "movement": step_movement,
        "blink": step_blink,
    }
    if step_smile is not None and step_smile.filename:
        uploads["smile"] = step_smile

    temp_paths: dict[str, Path] = {}
    try:
        for step_type, upload in uploads.items():
            temp_paths[step_type] = await _persist_upload(upload)
        return get_liveness_service().verify(
            temp_paths,
            challenge_id=challenge_id.strip() if challenge_id else None,
            person_id=person_id.strip() if person_id else None,
        )
    except ValueError as exc:
        return LivenessVerifyResponse(
            passed=False,
            score=0.0,
            message=str(exc),
            checks={"face_detected": False},
            method="mediapipe_v2",
        )
    except Exception as exc:
        message = str(exc).strip()
        if "match_face_embeddings" in message:
            message = (
                "Error de base de datos al comparar rostros. "
                "Ejecuta la migracion v3_fix_match_face_embeddings.sql en Supabase e intenta de nuevo."
            )
        else:
            message = f"Error temporal procesando liveness. Intenta de nuevo."
        return LivenessVerifyResponse(
            passed=False,
            score=0.0,
            message=message,
            checks={"face_detected": False},
            method="mediapipe_v2",
        )
    finally:
        for path in temp_paths.values():
            remove_file(path)


@router.post("/identify", response_model=IdentifyFaceResponse)
async def identify_face(file: UploadFile = File(...)) -> IdentifyFaceResponse:
    image_path = await _persist_upload(file)
    try:
        return match_face_from_image(image_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error identificando rostro: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.get("/registered", response_model=RegisteredFacesResponse)
def list_registered_faces() -> RegisteredFacesResponse:
    faces = get_schedule_service().enrich_faces(embedding_store.list_public())
    return RegisteredFacesResponse(faces=faces)


@router.patch("/employees/{person_id}", response_model=UpdateEmployeeResponse)
def update_employee(
    person_id: str,
    payload: UpdateEmployeeRequest,
) -> UpdateEmployeeResponse:
    if all(
        value is None
        for value in (
            payload.name,
            payload.email,
            payload.employee_code,
            payload.shift_code,
            payload.is_active,
        )
    ):
        raise HTTPException(status_code=400, detail="Envia al menos un campo para actualizar.")
    has_employee_update = any(
        value is not None
        for value in (payload.name, payload.email, payload.employee_code, payload.is_active)
    )
    try:
        if has_employee_update:
            person = embedding_store.update_employee(
                person_id,
                name=payload.name,
                email=payload.email,
                employee_code=payload.employee_code,
                is_active=payload.is_active,
            )
        else:
            person = _get_registered_employee(person_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.shift_code is not None:
        try:
            get_schedule_service().assign_shift(person_id, payload.shift_code)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        person = next(
            (
                face
                for face in get_schedule_service().enrich_faces(embedding_store.list_public())
                if face.person_id == person_id
            ),
            person,
        )

    if payload.is_active is False:
        message = f"Empleado {person.name} desactivado. Ya no podra escanearse."
    elif payload.is_active is True:
        message = f"Empleado {person.name} reactivado."
    else:
        message = f"Datos de {person.name} actualizados."

    return UpdateEmployeeResponse(person=person, message=message)


@router.delete("/employees/{person_id}", response_model=DeleteEmployeeResponse)
def delete_employee(person_id: str) -> DeleteEmployeeResponse:
    try:
        result = embedding_store.delete_employee(person_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    get_schedule_service().remove_assignment(person_id)

    r2_keys = result.pop("r2_keys", [])
    r2_objects_deleted = 0
    if r2_storage is not None and r2_keys:
        r2_objects_deleted = r2_storage.delete_objects(r2_keys)

    if settings.storage_backend.lower() != "supabase":
        result["attendance_events_deleted"] = attendance_event_store.delete_by_person(
            result["person_id"],
        )
        result["incidents_deleted"] = incident_store.delete_by_person(result["person_id"])

    deleted = DeleteEmployeeStats(
        embeddings=result.get("embeddings_deleted", 0),
        portraits=result.get("portraits_deleted", 0),
        attendance_events=result.get("attendance_events_deleted", 0),
        incidents=result.get("incidents_deleted", 0),
        liveness_checks=result.get("liveness_checks_deleted", 0),
        r2_objects=r2_objects_deleted,
    )
    name = result["name"]
    message = (
        f"{name} eliminado definitivamente. "
        f"Se borraron {deleted.embeddings} embedding(s), "
        f"{deleted.attendance_events} marca(s) de asistencia y "
        f"{deleted.incidents} incidencia(s)."
    )
    return DeleteEmployeeResponse(
        person_id=result["person_id"],
        name=name,
        message=message,
        deleted=deleted,
    )


@router.post("/employees/{person_id}/photo", response_model=UpdateEmployeePhotoResponse)
async def upload_employee_photo(
    person_id: str,
    file: UploadFile = File(...),
) -> UpdateEmployeePhotoResponse:
    employee = _get_registered_employee(person_id)
    image_path = await _persist_upload(file)
    content_type = file.content_type or "image/jpeg"
    try:
        stored, image_url, r2_saved, _, storage_message = await _upsert_face_from_image(
            person_id=employee.person_id,
            name=employee.name,
            email=employee.email,
            image_path=image_path,
            content_type=content_type,
        )
        person = next(
            (face for face in embedding_store.list_public() if face.person_id == stored.person_id),
            employee,
        )
        return UpdateEmployeePhotoResponse(
            person=person,
            message=storage_message or f"Foto de {person.name} actualizada.",
            image_url=image_url,
            r2_saved=r2_saved,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando foto: {exc}",
        ) from exc
    finally:
        remove_file(image_path)


@router.get("/portrait/{person_id}")
@router.get("/portrait/{person_id}/{pose_type}")
def get_face_portrait(person_id: str, pose_type: str = "front") -> FileResponse:
    portrait_path = embedding_store.get_portrait_path(person_id, pose_type=pose_type)
    if portrait_path is None:
        raise HTTPException(status_code=404, detail="No hay foto registrada para esta persona.")
    safe_id = sanitize_person_id(person_id)
    filename = f"{safe_id}.jpg" if pose_type == "front" else f"{safe_id}_{pose_type}.jpg"
    return FileResponse(
        path=portrait_path,
        media_type="image/jpeg",
        filename=filename,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/storage-status", response_model=StorageStatusResponse)
def get_storage_status() -> StorageStatusResponse:
    if r2_storage is None:
        return StorageStatusResponse(
            provider="cloudflare_r2",
            enabled=False,
            connected=False,
            bucket=settings.r2_bucket or None,
            message="R2 no esta configurado en variables de entorno.",
        )
    connected, message = r2_storage.verify_connection()
    return StorageStatusResponse(
        provider="cloudflare_r2",
        enabled=True,
        connected=connected,
        bucket=settings.r2_bucket,
        message=message,
    )


def _get_registered_employee(person_id: str):
    person_id = person_id.strip()
    employee = next(
        (face for face in embedding_store.list_public() if face.person_id == person_id),
        None,
    )
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"No existe empleado con person_id='{person_id}'.",
        )
    return employee


async def _upsert_face_from_image(
    *,
    person_id: str,
    name: str,
    email: str | None,
    image_path: Path,
    content_type: str,
    pose_type: str = "front",
    employee_code: str | None = None,
    area_code: str | None = None,
    position_code: str | None = None,
    area_name: str | None = None,
    position_name: str | None = None,
) -> tuple[object, str, bool, str | None, str]:
    embedding = face_ai_service.create_embedding(image_path)
    stored = embedding_store.save_embedding(
        person_id=person_id,
        name=name,
        model=settings.active_face_model,
        embedding=embedding,
        email=email,
        pose_type=pose_type,
        employee_code=employee_code,
        area_code=area_code,
        position_code=position_code,
        area_name=area_name,
        position_name=position_name,
    )
    image_url = embedding_store.save_portrait(stored.person_id, image_path, pose_type=pose_type)
    r2_saved = False
    image_key: str | None = None
    storage_message = f"Embedding ({pose_type}) guardado para escaneo."
    if r2_storage is not None:
        try:
            suffix = "register.jpg" if pose_type == "front" else f"pose-{pose_type}.jpg"
            object_key = _build_r2_object_key(
                person_id=stored.person_id,
                suffix=suffix,
                pose_type=pose_type,
            )
            uploaded = r2_storage.upload_file(
                file_path=image_path,
                object_key=object_key,
                content_type=content_type,
            )
            r2_saved = True
            image_key = uploaded.key
            if uploaded.public_url and pose_type == "front":
                image_url = uploaded.public_url
            storage_message = f"Pose {pose_type} guardada en panel, escaneo y R2."
            if settings.storage_backend.lower() == "supabase" and pose_type == "front":
                with get_conn() as conn:
                    org_id = resolve_org_id(conn)
                    save_face_asset(
                        conn,
                        org_id=org_id,
                        person_id=stored.person_id,
                        r2_key=uploaded.key,
                        public_url=uploaded.public_url,
                        content_type=content_type,
                        bytes_size=image_path.stat().st_size,
                    )
        except Exception as r2_exc:
            storage_message = f"Pose {pose_type} local OK, pero R2 fallo: {r2_exc}"
    return stored, image_url, r2_saved, image_key, storage_message


async def _persist_upload(file: UploadFile) -> Path:
    try:
        return await save_upload_to_temp_file(file, max_mb=settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _build_r2_object_key(person_id: str, suffix: str, pose_type: str = "front") -> str:
    now = datetime.now(UTC)
    sanitized = person_id.strip().replace("/", "_")
    if pose_type != "front":
        return (
            f"person/{sanitized}/poses/{pose_type}/"
            f"{now:%Y/%m/%d}/"
            f"{uuid4().hex}-{suffix}"
        )
    return (
        f"person/{sanitized}/raw/"
        f"{now:%Y/%m/%d}/"
        f"{uuid4().hex}-{suffix}"
    )


