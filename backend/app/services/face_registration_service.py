from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.face import MatchCandidate
from app.services.embedding_store import get_embedding_store, portrait_api_path
from app.services.face_ai_service import FaceAIService
from app.services.r2_storage_service import R2StorageService
from app.services.supabase_db import get_conn, resolve_org_id, save_face_asset
from app.utils.image_files import flip_image_horizontal, remove_file

face_ai_service = FaceAIService()
embedding_store = get_embedding_store()
r2_storage = R2StorageService() if settings.r2_enabled else None


class FaceAlreadyRegisteredError(ValueError):
    def __init__(self, match: MatchCandidate) -> None:
        self.match = match
        confidence = round(match.confidence * 100)
        super().__init__(
            "Este rostro ya esta registrado como "
            f"{match.name} ({match.person_id}) con {confidence}% de coincidencia. "
            "No puedes crear otro perfil con la misma persona."
        )


def get_register_duplicate_threshold() -> float:
    try:
        from app.services.admin_service import get_admin_service

        return get_admin_service().get_system_settings().face_scan_match_threshold
    except Exception:
        return settings.face_scan_match_threshold


def find_duplicate_face_in_image(
    image_path: Path,
    *,
    exclude_person_id: str | None = None,
) -> MatchCandidate | None:
    threshold = get_register_duplicate_threshold()
    model = settings.active_face_model
    flipped_path = flip_image_horizontal(image_path)
    best: MatchCandidate | None = None

    try:
        for path in (image_path, flipped_path):
            try:
                embedding = face_ai_service.create_embedding(path)
            except ValueError:
                continue
            match = embedding_store.find_existing_match(
                embedding=embedding,
                threshold=threshold,
                model=model,
                exclude_person_id=exclude_person_id,
            )
            if match is None:
                continue
            if best is None or match.distance < best.distance:
                best = match
    finally:
        remove_file(flipped_path)

    return best


def assert_face_not_already_registered(
    image_path: Path,
    *,
    exclude_person_id: str | None = None,
) -> None:
    match = find_duplicate_face_in_image(
        image_path,
        exclude_person_id=exclude_person_id,
    )
    if match is not None:
        raise FaceAlreadyRegisteredError(match)


def build_r2_object_key(person_id: str, suffix: str, pose_type: str = "front") -> str:
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


async def upsert_face_from_image(
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
    assert_face_not_already_registered(
        image_path,
        exclude_person_id=person_id.strip(),
    )
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
    panel_url = portrait_api_path(stored.person_id) if pose_type == "front" else image_url

    if r2_storage is not None:
        try:
            suffix = "register.jpg" if pose_type == "front" else f"pose-{pose_type}.jpg"
            object_key = build_r2_object_key(
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
            if pose_type == "front":
                image_url = uploaded.public_url or panel_url
            storage_message = f"Pose {pose_type} guardada en panel, escaneo y R2."
            if settings.storage_backend.lower() == "supabase" and pose_type == "front":
                with get_conn() as conn:
                    org_id = resolve_org_id(conn)
                    save_face_asset(
                        conn,
                        org_id=org_id,
                        person_id=stored.person_id,
                        r2_key=uploaded.key,
                        public_url=uploaded.public_url or panel_url,
                        content_type=content_type,
                        bytes_size=image_path.stat().st_size,
                    )
        except Exception as r2_exc:
            storage_message = f"Pose {pose_type} local OK, pero R2 fallo: {r2_exc}"
            if pose_type == "front" and settings.storage_backend.lower() == "supabase":
                _save_panel_face_asset(
                    person_id=stored.person_id,
                    content_type=content_type,
                    bytes_size=image_path.stat().st_size,
                    public_url=panel_url,
                )
    elif pose_type == "front" and settings.storage_backend.lower() == "supabase":
        _save_panel_face_asset(
            person_id=stored.person_id,
            content_type=content_type,
            bytes_size=image_path.stat().st_size,
            public_url=panel_url,
        )

    return stored, image_url, r2_saved, image_key, storage_message


def _save_panel_face_asset(
    *,
    person_id: str,
    content_type: str,
    bytes_size: int,
    public_url: str,
    r2_key: str = "",
) -> None:
    with get_conn() as conn:
        org_id = resolve_org_id(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                delete from public.face_assets
                where org_id = %s and person_id = %s
                """,
                (org_id, person_id),
            )
        save_face_asset(
            conn,
            org_id=org_id,
            person_id=person_id,
            r2_key=r2_key,
            public_url=public_url,
            content_type=content_type,
            bytes_size=bytes_size,
        )
