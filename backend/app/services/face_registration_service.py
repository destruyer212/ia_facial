from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.tenant import get_active_org_code
from app.core.workload import run_face_job
from app.schemas.face import MatchCandidate
from app.services.anti_spoof_service import AntiSpoofService
from app.services.embedding_store import get_embedding_store, portrait_api_path
from app.services.face_ai_service import FaceAIService
from app.services.r2_storage_service import R2StorageService
from app.services.supabase_db import get_conn, resolve_org_id, save_face_asset
from app.utils.image_files import flip_image_horizontal, remove_file

face_ai_service = FaceAIService()
embedding_store = get_embedding_store()
anti_spoof_service = AntiSpoofService()
r2_storage = R2StorageService() if settings.r2_enabled else None


class FaceNotLiveError(ValueError):
    def __init__(self, pose_type: str, live_score: float) -> None:
        self.pose_type = pose_type
        self.live_score = live_score
        score_pct = round(live_score * 100)
        super().__init__(
            f"No se detecto rostro humano en vivo en la pose {pose_type} "
            f"(validacion anti-spoof {score_pct}%). "
            "No uses fotos, pantallas, impresiones ni otro telefono. "
            "Mira directo a la camara de este dispositivo."
        )


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
    strict_threshold = settings.register_duplicate_match_threshold
    try:
        from app.services.admin_service import get_admin_service

        scan_threshold = get_admin_service().get_system_settings().face_scan_match_threshold
    except Exception:
        scan_threshold = settings.face_scan_match_threshold
    return min(strict_threshold, scan_threshold)


def get_register_anti_spoof_threshold() -> float:
    return settings.register_min_anti_spoof_score


def assert_image_is_live(image_path: Path, pose_type: str) -> None:
    result = anti_spoof_service.analyze(
        image_path,
        min_live_score=get_register_anti_spoof_threshold(),
    )
    if not result.is_live:
        raise FaceNotLiveError(pose_type, result.live_score)


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
    org_code = get_active_org_code()
    sanitized = person_id.strip().replace("/", "_")
    if pose_type != "front":
        return (
            f"org/{org_code}/person/{sanitized}/poses/{pose_type}/"
            f"{now:%Y/%m/%d}/"
            f"{uuid4().hex}-{suffix}"
        )
    return (
        f"org/{org_code}/person/{sanitized}/raw/"
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
    return await run_face_job(
        lambda: _upsert_face_from_image_sync(
            person_id=person_id,
            name=name,
            email=email,
            image_path=image_path,
            content_type=content_type,
            pose_type=pose_type,
            employee_code=employee_code,
            area_code=area_code,
            position_code=position_code,
            area_name=area_name,
            position_name=position_name,
        )
    )


def _upsert_face_from_image_sync(
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
    assert_image_is_live(image_path, pose_type)
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
    safe_key = r2_key or f"panel/{get_active_org_code()}/person/{person_id.strip().replace('/', '_')}/{uuid4().hex}.jpg"
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
            r2_key=safe_key,
            public_url=public_url,
            content_type=content_type,
            bytes_size=bytes_size,
        )
