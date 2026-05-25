from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.face import (
    AnalyzeFaceResponse,
    EmbeddingResponse,
    FaceDetectionResponse,
    IdentifyFaceResponse,
    RegisteredFacesResponse,
    RegisterFaceResponse,
)
from app.services.embedding_store import LocalEmbeddingStore
from app.services.face_ai_service import FaceAIService
from app.services.opencv_service import OpenCVService
from app.utils.image_files import remove_file, save_upload_to_temp_file

router = APIRouter()
opencv_service = OpenCVService()
face_ai_service = FaceAIService()
embedding_store = LocalEmbeddingStore()


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
            model=settings.deepface_model,
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
    file: UploadFile = File(...),
) -> RegisterFaceResponse:
    image_path = await _persist_upload(file)
    try:
        embedding = face_ai_service.create_embedding(image_path)
        stored = embedding_store.save_embedding(
            person_id=person_id,
            name=name,
            model=settings.deepface_model,
            embedding=embedding,
        )
        return RegisterFaceResponse(
            person_id=stored.person_id,
            name=stored.name,
            model=stored.model,
            total_embeddings=embedding_store.count(),
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


@router.post("/identify", response_model=IdentifyFaceResponse)
async def identify_face(file: UploadFile = File(...)) -> IdentifyFaceResponse:
    image_path = await _persist_upload(file)
    try:
        embedding = face_ai_service.create_embedding(image_path)
        match = embedding_store.find_best_match(
            embedding=embedding,
            threshold=settings.face_match_threshold,
            model=settings.deepface_model,
        )
        return IdentifyFaceResponse(
            matched=match is not None,
            threshold=settings.face_match_threshold,
            candidate=match,
        )
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
    return RegisteredFacesResponse(faces=embedding_store.list_public())


async def _persist_upload(file: UploadFile) -> Path:
    try:
        return await save_upload_to_temp_file(file, max_mb=settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
