from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
from fastapi import UploadFile

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXTENSIONS_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
def sniff_image_content_type(payload: bytes) -> str | None:
    if len(payload) >= 3 and payload[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(payload) >= 8 and payload[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


def resolve_upload_content_type(content_type: str | None, payload: bytes) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized in ALLOWED_CONTENT_TYPES:
        return normalized

    sniffed = sniff_image_content_type(payload)
    if sniffed:
        return sniffed

    raise ValueError("Formato no soportado. Use JPG, PNG o WEBP.")


async def save_upload_to_temp_file(file: UploadFile, max_mb: int) -> Path:
    payload = await file.read()
    if not payload:
        raise ValueError("El archivo esta vacio.")

    content_type = resolve_upload_content_type(file.content_type, payload)

    max_bytes = max_mb * 1024 * 1024
    if len(payload) > max_bytes:
        raise ValueError(f"El archivo supera el limite de {max_mb} MB.")

    suffix = EXTENSIONS_BY_CONTENT_TYPE.get(content_type, ".jpg")
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(payload)
        return Path(temp_file.name)


def remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def flip_image_horizontal(source: Path) -> Path:
    """Copia espejada para comparar selfies de celular vs webcam."""
    image = cv2.imread(str(source))
    if image is None:
        raise ValueError("No se pudo leer la imagen para espejar.")

    flipped = cv2.flip(image, 1)
    suffix = source.suffix if source.suffix else ".jpg"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        if not cv2.imwrite(temp_file.name, flipped):
            raise ValueError("No se pudo guardar la imagen espejada.")
        return Path(temp_file.name)

