"""
Repara fotos de panel para empleados ya registrados.
Busca imagenes en R2 y/o disco local y registra face_assets en Supabase.

Uso:
  cd backend
  .venv\\Scripts\\python.exe ..\\scripts\\repair_face_photos.py TI-JT-0001
  .venv\\Scripts\\python.exe ..\\scripts\\repair_face_photos.py --all-missing
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.services.embedding_store import (  # noqa: E402
    get_embedding_store,
    portrait_api_path,
)
from app.services.r2_storage_service import R2StorageService  # noqa: E402
from app.services.supabase_db import get_conn, resolve_org_id  # noqa: E402
from app.services.face_registration_service import _save_panel_face_asset  # noqa: E402


def list_r2_front_keys(r2: R2StorageService, person_id: str) -> list[str]:
    sanitized = person_id.strip().replace("/", "_")
    prefix = f"person/{sanitized}/"
    client = r2._client
    keys: list[str] = []
    token = None
    while True:
        kwargs = {"Bucket": r2.bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = item.get("Key")
            if key and "/raw/" in key:
                keys.append(key)
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
    keys.sort(reverse=True)
    return keys


def download_r2_object(r2: R2StorageService, key: str, dest: Path) -> None:
    r2._client.download_file(r2.bucket, key, str(dest))


def repair_person(person_id: str, *, dry_run: bool = False) -> str:
    store = get_embedding_store()
    local = store.get_portrait_path(person_id, pose_type="front")
    panel_url = portrait_api_path(person_id)

    if not settings.r2_enabled:
        if local and local.exists():
            if dry_run:
                return f"{person_id}: OK local {local}"
            _save_panel_face_asset(
                person_id=person_id,
                content_type="image/jpeg",
                bytes_size=local.stat().st_size,
                public_url=panel_url,
            )
            return f"{person_id}: face_asset actualizado desde disco local"
        return f"{person_id}: sin foto local ni R2"

    r2 = R2StorageService()
    keys = list_r2_front_keys(r2, person_id)
    public_base = settings.r2_public_base_url.rstrip("/")

    if keys:
        key = keys[0]
        public_url = f"{public_base}/{key}" if public_base else panel_url
        if dry_run:
            return f"{person_id}: encontrado en R2 {key}"
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            download_r2_object(r2, key, tmp_path)
            store.save_portrait(person_id, tmp_path, pose_type="front")
            _save_panel_face_asset(
                person_id=person_id,
                content_type="image/jpeg",
                bytes_size=tmp_path.stat().st_size,
                public_url=public_url,
                r2_key=key,
            )
            return f"{person_id}: reparado desde R2 ({key})"
        finally:
            tmp_path.unlink(missing_ok=True)

    if local and local.exists():
        if dry_run:
            return f"{person_id}: solo disco {local}"
        _save_panel_face_asset(
            person_id=person_id,
            content_type="image/jpeg",
            bytes_size=local.stat().st_size,
            public_url=panel_url,
        )
        return f"{person_id}: face_asset desde disco local"

    return f"{person_id}: sin imagen en R2 ni en disco"


def persons_missing_image() -> list[str]:
    store = get_embedding_store()
    return [face.person_id for face in store.list_public() if not face.image_url]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("person_ids", nargs="*", help="IDs a reparar, ej. TI-JT-0001")
    parser.add_argument("--all-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = list(args.person_ids)
    if args.all_missing:
        targets.extend(persons_missing_image())
    targets = list(dict.fromkeys(targets))
    if not targets:
        print("Indica person_id o --all-missing")
        return 1

    # Verificar conexion supabase
    with get_conn() as conn:
        resolve_org_id(conn)

    for person_id in targets:
        print(repair_person(person_id, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
