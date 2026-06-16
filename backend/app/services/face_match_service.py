from pathlib import Path

from app.core.config import settings
from app.schemas.face import IdentifyFaceResponse, MatchCandidate
from app.services.embedding_store import get_embedding_store
from app.services.face_ai_service import FaceAIService
from app.utils.image_files import flip_image_horizontal, remove_file

face_ai_service = FaceAIService()
embedding_store = get_embedding_store()


def get_runtime_scan_threshold() -> float:
    try:
        from app.services.admin_service import get_admin_service

        return get_admin_service().get_system_settings().face_scan_match_threshold
    except Exception:
        return settings.face_scan_match_threshold


def match_face_from_image(image_path: Path) -> IdentifyFaceResponse:
    """
    Compara el rostro con y sin espejo horizontal.
    Celular y PC guardan selfies con orientaciones distintas; probar ambas evita falsos negativos.
    """
    threshold = get_runtime_scan_threshold()
    model = settings.active_face_model
    flipped_path = flip_image_horizontal(image_path)

    best: MatchCandidate | None = None
    try:
        for path in (image_path, flipped_path):
            try:
                embedding = face_ai_service.create_embedding(path)
            except ValueError:
                continue
            candidate = embedding_store.find_best_match(
                embedding=embedding,
                threshold=threshold,
                model=model,
            )
            if candidate is None:
                continue
            if best is None or candidate.distance < best.distance:
                best = candidate
    finally:
        remove_file(flipped_path)

    near_miss: MatchCandidate | None = None
    if best is None:
        try:
            embedding = face_ai_service.create_embedding(image_path)
            near_miss = embedding_store.find_nearest_candidate(
                embedding=embedding,
                model=model,
            )
        except ValueError:
            pass

    return IdentifyFaceResponse(
        matched=best is not None,
        threshold=threshold,
        candidate=best,
        near_miss=near_miss,
    )
