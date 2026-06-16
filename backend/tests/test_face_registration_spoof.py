from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.anti_spoof_service import AntiSpoofResult
from app.services.face_registration_service import FaceNotLiveError, assert_image_is_live


def test_assert_image_is_live_rejects_spoof(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    image_path = tmp_path / "screen.jpg"
    image_path.write_bytes(b"fake")

    mock_service = MagicMock()
    mock_service.analyze.return_value = AntiSpoofResult(
        live_score=0.12,
        is_live=False,
        fft_score=0.1,
        color_score=0.1,
        specular_score=0.1,
    )
    monkeypatch.setattr(
        "app.services.face_registration_service.anti_spoof_service",
        mock_service,
    )
    monkeypatch.setattr(
        "app.services.face_registration_service.get_register_anti_spoof_threshold",
        lambda: 0.38,
    )

    with pytest.raises(FaceNotLiveError) as exc:
        assert_image_is_live(image_path, "front")

    assert exc.value.pose_type == "front"
    assert "vivo" in str(exc.value).lower()
