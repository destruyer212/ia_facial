from pathlib import Path
from typing import Any

from app.services.face_engine import get_face_engine


class FaceAIService:
    def __init__(self) -> None:
        self._engine = get_face_engine()

    @property
    def model_name(self) -> str:
        return self._engine.model_name

    def analyze_image(self, image_path: Path) -> dict[str, Any]:
        return self._engine.analyze_image(image_path)

    def create_embedding(self, image_path: Path) -> list[float]:
        return self._engine.create_embedding(image_path)
