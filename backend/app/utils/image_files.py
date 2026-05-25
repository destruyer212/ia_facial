from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXTENSIONS_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def save_upload_to_temp_file(file: UploadFile, max_mb: int) -> Path:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Formato no soportado. Use JPG, PNG o WEBP.")

    payload = await file.read()
    if not payload:
        raise ValueError("El archivo esta vacio.")

    max_bytes = max_mb * 1024 * 1024
    if len(payload) > max_bytes:
        raise ValueError(f"El archivo supera el limite de {max_mb} MB.")

    suffix = EXTENSIONS_BY_CONTENT_TYPE.get(file.content_type, ".jpg")
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(payload)
        return Path(temp_file.name)


def remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

