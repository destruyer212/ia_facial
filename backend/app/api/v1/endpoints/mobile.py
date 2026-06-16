import asyncio
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.face import RegisterFaceProfileResponse
from app.services.embedding_store import get_embedding_store
from app.services.face_registration_service import upsert_face_from_image
from app.services.registration_token_service import get_registration_token_service
from app.services.schedule_service import get_schedule_service
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
embedding_store = get_embedding_store()
registration_service = get_registration_token_service()


@router.post("/faces/register-profile", response_model=RegisterFaceProfileResponse)
async def mobile_register_face_profile(
    token: str = Form(...),
    front: UploadFile = File(...),
    left: UploadFile = File(...),
    right: UploadFile = File(...),
) -> RegisterFaceProfileResponse:
    try:
        worker = registration_service.worker_for_valid_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    person_id = worker["employee_code"]
    uploads: dict[str, UploadFile] = {
        "front": front,
        "left": left,
        "right": right,
    }
    temp_paths: list[Path] = []
    poses_saved: list[str] = []
    image_url: str | None = None
    r2_saved_any = False
    storage_messages: list[str] = []
    stored = None

    try:
        for pose_type, upload in uploads.items():
            image_path = await _persist_upload(upload)
            temp_paths.append(image_path)
            content_type = upload.content_type or "image/jpeg"
            stored, pose_url, pose_r2, _, pose_msg = await upsert_face_from_image(
                person_id=person_id,
                name=worker["name"],
                email=worker["email"],
                image_path=image_path,
                content_type=content_type,
                pose_type=pose_type,
                employee_code=worker["employee_code"],
                area_code=worker["area_code"],
                position_code=worker["position_code"],
                area_name=worker["area_name"],
                position_name=worker["position_name"],
            )
            poses_saved.append(pose_type)
            r2_saved_any = r2_saved_any or pose_r2
            storage_messages.append(pose_msg)
            if pose_type == "front":
                image_url = pose_url

        get_schedule_service().assign_shift(person_id, worker["shift_code"])
        registration_service.complete_token(token)
        return RegisterFaceProfileResponse(
            person_id=stored.person_id if stored else person_id,
            name=stored.name if stored else worker["name"],
            model=stored.model if stored else settings.active_face_model,
            poses_saved=poses_saved,
            total_embeddings=embedding_store.count(),
            embedding_count=embedding_store.count_person_embeddings(person_id),
            r2_saved=r2_saved_any,
            image_url=image_url,
            storage_message="; ".join(storage_messages) or "Perfil facial movil guardado.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error registrando rostro movil: {exc}") from exc
    finally:
        for path in temp_paths:
            remove_file(path)


async def _persist_upload(file: UploadFile) -> Path:
    try:
        return await save_upload_to_temp_file(file, max_mb=settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
