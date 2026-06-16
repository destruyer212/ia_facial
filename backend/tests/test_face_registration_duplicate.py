from pathlib import Path

import pytest

from app.services.embedding_store import LocalEmbeddingStore
from app.services.face_registration_service import FaceAlreadyRegisteredError, assert_face_not_already_registered


def _unit_vector(value: float) -> list[float]:
    vector = [0.0] * 512
    vector[0] = value
    return vector


def test_find_existing_match_detects_other_person(tmp_path: Path) -> None:
    store = LocalEmbeddingStore(path=tmp_path / "embeddings.json")
    store.save_embedding("FN-CF-0001", "Destroyer 212", "Facenet512", _unit_vector(1.0))
    near = _unit_vector(0.99)

    match = store.find_existing_match(
        near,
        threshold=0.05,
        model="Facenet512",
    )

    assert match is not None
    assert match.person_id == "FN-CF-0001"
    assert match.name == "Destroyer 212"


def test_find_existing_match_ignores_same_person(tmp_path: Path) -> None:
    store = LocalEmbeddingStore(path=tmp_path / "embeddings.json")
    store.save_embedding("FN-CF-0001", "Destroyer 212", "Facenet512", _unit_vector(1.0))
    near = _unit_vector(0.99)

    match = store.find_existing_match(
        near,
        threshold=0.05,
        model="Facenet512",
        exclude_person_id="FN-CF-0001",
    )

    assert match is None


def test_assert_face_not_already_registered_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = LocalEmbeddingStore(path=tmp_path / "embeddings.json")
    store.save_embedding("FN-CF-0001", "Destroyer 212", "Facenet512", _unit_vector(1.0))

    image_path = tmp_path / "face.jpg"
    image_path.write_bytes(b"fake")

    class FakeFaceAI:
        def create_embedding(self, path: Path) -> list[float]:
            return _unit_vector(0.99)

    monkeypatch.setattr(
        "app.services.face_registration_service.embedding_store",
        store,
    )
    monkeypatch.setattr(
        "app.services.face_registration_service.face_ai_service",
        FakeFaceAI(),
    )
    monkeypatch.setattr(
        "app.services.face_registration_service.flip_image_horizontal",
        lambda path: path,
    )
    monkeypatch.setattr(
        "app.services.face_registration_service.remove_file",
        lambda path: None,
    )

    with pytest.raises(FaceAlreadyRegisteredError) as exc:
        assert_face_not_already_registered(image_path, exclude_person_id="TI-DS-0001")

    assert exc.value.match.person_id == "FN-CF-0001"
