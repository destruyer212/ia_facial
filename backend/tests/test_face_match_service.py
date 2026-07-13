from pathlib import Path

from app.schemas.face import MatchCandidate
from app.services.face_match_service import match_face_from_image


class _FakeFaceAI:
    def create_embedding(self, path: Path) -> list[float]:
        return [1.0] + [0.0] * 511


class _FakeAmbiguousStore:
    def find_top_matches(self, **kwargs):
        return [
            MatchCandidate(
                person_id="TI-SA-0001",
                name="Dayanna Castillo",
                model="Facenet512",
                distance=0.31,
                confidence=0.69,
            ),
            MatchCandidate(
                person_id="TI-SA-0002",
                name="Diego Chancafe",
                model="Facenet512",
                distance=0.34,
                confidence=0.66,
            ),
        ]


class _FakeClearStore:
    def find_top_matches(self, **kwargs):
        return [
            MatchCandidate(
                person_id="TI-SA-0002",
                name="Diego Chancafe",
                model="Facenet512",
                distance=0.25,
                confidence=0.75,
            ),
            MatchCandidate(
                person_id="TI-SA-0001",
                name="Dayanna Castillo",
                model="Facenet512",
                distance=0.38,
                confidence=0.62,
            ),
        ]


def test_match_face_rejects_ambiguous_identity(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "scan.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr("app.services.face_match_service.face_ai_service", _FakeFaceAI())
    monkeypatch.setattr("app.services.face_match_service.embedding_store", _FakeAmbiguousStore())
    monkeypatch.setattr("app.services.face_match_service.flip_image_horizontal", lambda path: path)
    monkeypatch.setattr("app.services.face_match_service.remove_file", lambda path: None)
    monkeypatch.setattr("app.services.face_match_service.get_runtime_scan_threshold", lambda: 0.40)
    monkeypatch.setattr("app.services.face_match_service.settings.face_scan_ambiguous_margin", 0.05)

    result = match_face_from_image(image_path)

    assert result.matched is False
    assert result.ambiguous is True
    assert result.near_miss is not None
    assert result.second_candidate is not None


def test_match_face_accepts_clear_identity(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "scan.jpg"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr("app.services.face_match_service.face_ai_service", _FakeFaceAI())
    monkeypatch.setattr("app.services.face_match_service.embedding_store", _FakeClearStore())
    monkeypatch.setattr("app.services.face_match_service.flip_image_horizontal", lambda path: path)
    monkeypatch.setattr("app.services.face_match_service.remove_file", lambda path: None)
    monkeypatch.setattr("app.services.face_match_service.get_runtime_scan_threshold", lambda: 0.40)
    monkeypatch.setattr("app.services.face_match_service.settings.face_scan_ambiguous_margin", 0.05)

    result = match_face_from_image(image_path)

    assert result.matched is True
    assert result.ambiguous is False
    assert result.candidate is not None
    assert result.candidate.person_id == "TI-SA-0002"
