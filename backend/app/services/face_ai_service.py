from pathlib import Path
from typing import Any

from app.core.config import settings


class FaceAIService:
    def analyze_image(self, image_path: Path) -> dict[str, Any]:
        deepface = self._deepface()
        result = deepface.analyze(
            img_path=str(image_path),
            actions=["age", "gender", "emotion", "race"],
            detector_backend=settings.deepface_detector_backend,
            enforce_detection=False,
        )
        item = result[0] if isinstance(result, list) else result
        safe_item = _to_builtin(item)
        return {
            "age": safe_item.get("age"),
            "dominant_gender": safe_item.get("dominant_gender"),
            "dominant_emotion": safe_item.get("dominant_emotion"),
            "dominant_race": safe_item.get("dominant_race"),
            "raw": safe_item,
        }

    def create_embedding(self, image_path: Path) -> list[float]:
        deepface = self._deepface()
        representations = deepface.represent(
            img_path=str(image_path),
            model_name=settings.deepface_model,
            detector_backend=settings.deepface_detector_backend,
            enforce_detection=False,
        )
        if not representations:
            raise ValueError("No se pudo generar embedding facial.")

        first = representations[0]
        embedding = first.get("embedding")
        if not embedding:
            raise ValueError("DeepFace no devolvio un embedding valido.")
        return [float(value) for value in embedding]

    @staticmethod
    def _deepface():
        from deepface import DeepFace

        return DeepFace


def _to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value
