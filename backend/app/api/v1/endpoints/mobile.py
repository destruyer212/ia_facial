from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.face import RegisterFaceProfileResponse
from app.services.embedding_store import get_embedding_store
from app.services.face_ai_service import FaceAIService
from app.services.registration_token_service import get_registration_token_service
from app.services.schedule_service import get_schedule_service
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
face_ai_service = FaceAIService()
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
    try:
        for pose_type, upload in uploads.items():
            image_path = await _persist_upload(upload)
            temp_paths.append(image_path)
            embedding = face_ai_service.create_embedding(image_path)
            stored = embedding_store.save_embedding(
                person_id=person_id,
                name=worker["name"],
                model=settings.active_face_model,
                embedding=embedding,
                email=worker["email"],
                pose_type=pose_type,
                employee_code=worker["employee_code"],
                area_code=worker["area_code"],
                position_code=worker["position_code"],
                area_name=worker["area_name"],
                position_name=worker["position_name"],
            )
            pose_url = embedding_store.save_portrait(person_id, image_path, pose_type=pose_type)
            if pose_type == "front":
                image_url = pose_url
            poses_saved.append(pose_type)

        get_schedule_service().assign_shift(person_id, worker["shift_code"])
        registration_service.complete_token(token)
        return RegisterFaceProfileResponse(
            person_id=stored.person_id,
            name=stored.name,
            model=stored.model,
            poses_saved=poses_saved,
            total_embeddings=embedding_store.count(),
            embedding_count=embedding_store.count_person_embeddings(person_id),
            r2_saved=False,
            image_url=image_url,
            storage_message="Perfil facial movil guardado y token marcado como usado.",
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
