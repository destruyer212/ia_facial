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

        configured = get_admin_service().get_system_settings().face_scan_match_threshold
    except Exception:
        configured = settings.face_scan_match_threshold
    return min(configured, settings.face_scan_max_match_threshold)


def match_face_from_image(image_path: Path) -> IdentifyFaceResponse:
    """
    Compara el rostro con y sin espejo horizontal.
    Celular y PC guardan selfies con orientaciones distintas; probar ambas evita falsos negativos.
    """
    threshold = get_runtime_scan_threshold()
    model = settings.active_face_model
    flipped_path = flip_image_horizontal(image_path)

    best_by_person: dict[str, MatchCandidate] = {}
    try:
        for path in (image_path, flipped_path):
            try:
                embedding = face_ai_service.create_embedding(path)
            except ValueError:
                continue
            candidates = embedding_store.find_top_matches(
                embedding=embedding,
                model=model,
                limit=5,
            )
            for candidate in candidates:
                current = best_by_person.get(candidate.person_id)
                if current is None or candidate.distance < current.distance:
                    best_by_person[candidate.person_id] = candidate
    finally:
        remove_file(flipped_path)

    ranked = sorted(best_by_person.values(), key=lambda item: item.distance)
    best = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    if best is None:
        return IdentifyFaceResponse(
            matched=False,
            threshold=threshold,
            message="No se detecto un rostro comparable.",
        )

    if best.distance > threshold:
        return IdentifyFaceResponse(
            matched=False,
            threshold=threshold,
            near_miss=best,
            second_candidate=second,
            message="Rostro no reconocido con suficiente seguridad.",
        )

    if second is not None and (second.distance - best.distance) < settings.face_scan_ambiguous_margin:
        return IdentifyFaceResponse(
            matched=False,
            threshold=threshold,
            near_miss=best,
            second_candidate=second,
            ambiguous=True,
            message=(
                "Rostro ambiguo: se parece a mas de un trabajador. "
                "No se registrara asistencia; repite el escaneo con mejor luz."
            ),
        )

    return IdentifyFaceResponse(
        matched=True,
        threshold=threshold,
        candidate=best,
        second_candidate=second,
        message="Identidad confirmada.",
    )
