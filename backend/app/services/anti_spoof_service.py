from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class AntiSpoofResult:
    live_score: float
    is_live: bool
    fft_score: float
    color_score: float
    specular_score: float


class AntiSpoofService:
    """Clasificador ligero print/replay (Fase 4). Sin PyTorch — heurísticas + FFT + color."""

    def __init__(self) -> None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(str(cascade_path))

    def analyze(self, image_path: Path, *, min_live_score: float) -> AntiSpoofResult:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("No se pudo leer imagen para anti-spoofing.")

        face = _largest_face_crop(image, self._cascade)
        if face is None:
            return AntiSpoofResult(
                live_score=0.0,
                is_live=False,
                fft_score=0.0,
                color_score=0.0,
                specular_score=0.0,
            )

        fft_score = _fft_live_score(face)
        color_score = _color_live_score(face)
        specular_score = _specular_live_score(face)
        live_score = float(
            0.40 * fft_score + 0.35 * color_score + 0.25 * specular_score
        )
        return AntiSpoofResult(
            live_score=round(live_score, 4),
            is_live=live_score >= min_live_score,
            fft_score=round(fft_score, 4),
            color_score=round(color_score, 4),
            specular_score=round(specular_score, 4),
        )


def _largest_face_crop(image: np.ndarray, cascade: cv2.CascadeClassifier) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        h, w = gray.shape
        size = min(h, w)
        y1 = (h - size) // 2
        x1 = (w - size) // 2
        return image[y1 : y1 + size, x1 : x1 + size]

    x, y, fw, fh = max(faces, key=lambda item: item[2] * item[3])
    pad = int(max(fw, fh) * 0.15)
    h, w = image.shape[:2]
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w, x + fw + pad)
    y2 = min(h, y + fh + pad)
    return image[y1:y2, x1:x2]


def _fft_live_score(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128))
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    radius = 12
    mask = np.ones((h, w), np.uint8)
    cv2.circle(mask, (cx, cy), radius, 0, -1)
    low = magnitude[mask == 0].mean() or 1.0
    high = magnitude[mask == 1].mean() or 0.0
    ratio = high / low
    # Webcam/browser JPEG reduce altas frecuencias; umbrales mas tolerantes.
    return float(np.clip((ratio - 0.03) / 0.22, 0.0, 1.0))


def _color_live_score(face: np.ndarray) -> float:
    hsv = cv2.cvtColor(face, cv2.COLOR_BGR2HSV)
    h_channel = hsv[:, :, 0].astype(np.float32)
    s_channel = hsv[:, :, 1].astype(np.float32)
    hue_std = hsv[:, :, 0].std()
    sat_mean = s_channel.mean()
    sat_std = s_channel.std()
    score = 0.0
    score += np.clip(hue_std / 18.0, 0.0, 1.0) * 0.45
    score += np.clip(sat_std / 35.0, 0.0, 1.0) * 0.35
    score += np.clip((sat_mean - 20.0) / 80.0, 0.0, 1.0) * 0.20
    return float(np.clip(score, 0.0, 1.0))


def _specular_live_score(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    bright = (gray > 220).mean()
    dark = (gray < 35).mean()
    contrast = gray.std()
    score = np.clip(contrast / 32.0, 0.0, 1.0)
    if bright > 0.45:
        score *= 0.75
    if dark > 0.50:
        score *= 0.80
    return float(np.clip(score, 0.0, 1.0))
