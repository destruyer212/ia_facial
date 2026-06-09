from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import settings

_insightface_app = None


class FaceEngine(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_embedding(self, image_path: Path) -> list[float]:
        raise NotImplementedError

    def analyze_image(self, image_path: Path) -> dict[str, Any]:
        raise NotImplementedError(f"Analisis demografico no disponible en {self.model_name}.")


class DeepFaceEngine(FaceEngine):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.deepface_model

    @property
    def model_name(self) -> str:
        return self._model_name

    def create_embedding(self, image_path: Path) -> list[float]:
        deepface = self._deepface()
        representations = deepface.represent(
            img_path=str(image_path),
            model_name=self._model_name,
            detector_backend=settings.deepface_detector_backend,
            enforce_detection=False,
        )
        if not representations:
            raise ValueError("No se pudo generar embedding facial.")
        embedding = representations[0].get("embedding")
        if not embedding:
            raise ValueError("DeepFace no devolvio un embedding valido.")
        return [float(value) for value in embedding]

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

    @staticmethod
    def _deepface():
        from deepface import DeepFace

        return DeepFace


class InsightFaceEngine(FaceEngine):
    @property
    def model_name(self) -> str:
        return f"arcface_{settings.insightface_model}"

    def create_embedding(self, image_path: Path) -> list[float]:
        import cv2

        app = _get_insightface_app()
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("No se pudo leer la imagen enviada.")

        faces = app.get(image)
        if not faces:
            raise ValueError("InsightFace no detecto rostro en la imagen.")

        face = max(
            faces,
            key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]),
        )
        embedding = getattr(face, "embedding", None)
        if embedding is None:
            raise ValueError("InsightFace no devolvio embedding.")
        return [float(value) for value in embedding.tolist()]

    def analyze_image(self, image_path: Path) -> dict[str, Any]:
        import cv2

        app = _get_insightface_app()
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("No se pudo leer la imagen enviada.")

        faces = app.get(image)
        if not faces:
            raise ValueError("InsightFace no detecto rostro en la imagen.")

        face = max(
            faces,
            key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]),
        )
        gender = None
        if getattr(face, "gender", None) is not None:
            gender = "Man" if int(face.gender) == 1 else "Woman"
        return {
            "age": int(face.age) if getattr(face, "age", None) is not None else None,
            "dominant_gender": gender,
            "dominant_emotion": None,
            "dominant_race": None,
            "raw": {
                "bbox": [float(v) for v in face.bbox],
                "det_score": float(getattr(face, "det_score", 0.0)),
            },
        }


def get_face_engine() -> FaceEngine:
    engine = settings.face_engine.lower().strip()
    if engine == "insightface":
        return InsightFaceEngine()
    if engine == "arcface":
        return DeepFaceEngine(model_name="ArcFace")
    return DeepFaceEngine(model_name=settings.deepface_model)


def _get_insightface_app():
    global _insightface_app
    if _insightface_app is None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError(
                "InsightFace no esta instalado. En Windows usa FACE_ENGINE=arcface "
                "(DeepFace ArcFace) o instala Visual C++ Build Tools + pip install insightface onnxruntime."
            ) from exc
        app = FaceAnalysis(name=settings.insightface_model)
        app.prepare(ctx_id=0, det_size=(640, 640))
        _insightface_app = app
    return _insightface_app


def _to_builtin(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_builtin(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value
