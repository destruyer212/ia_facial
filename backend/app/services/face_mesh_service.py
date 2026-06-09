from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
NOSE_TIP = 1
LEFT_CHEEK = 234
RIGHT_CHEEK = 454
MOUTH_TOP = 13
MOUTH_BOTTOM = 14
MOUTH_LEFT = 78
MOUTH_RIGHT = 308


@dataclass
class FaceMeshAnalysis:
    face_detected: bool
    ear_left: float
    ear_right: float
    ear_avg: float
    mar: float
    yaw_proxy: float
    texture_score: float
    eyes_open: bool
    mouth_open: bool
    face_x: float = 0.0
    face_y: float = 0.0
    face_width: float = 0.0
    face_height: float = 0.0


class FaceMeshService:
    """Landmarks con MediaPipe Face Mesh (Fase 2b): parpadeo EAR y giro de cabeza."""

    def __init__(self) -> None:
        import mediapipe as mp

        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.4,
        )

    def analyze(
        self,
        image_path: Path,
        *,
        ear_open_min: float,
        mar_open_min: float = 0.28,
    ) -> FaceMeshAnalysis:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("No se pudo leer la imagen para analisis de malla facial.")

        height, width = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return FaceMeshAnalysis(
                face_detected=False,
                ear_left=0.0,
                ear_right=0.0,
                ear_avg=0.0,
                mar=0.0,
                yaw_proxy=0.0,
                texture_score=0.0,
                eyes_open=False,
                mouth_open=False,
            )

        landmarks = result.multi_face_landmarks[0].landmark
        xs = [landmarks[i].x * width for i in range(len(landmarks))]
        ys = [landmarks[i].y * height for i in range(len(landmarks))]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        face_w = max(x2 - x1, 1.0)
        face_h = max(y2 - y1, 1.0)
        ear_left = _eye_aspect_ratio(landmarks, LEFT_EYE, width, height)
        ear_right = _eye_aspect_ratio(landmarks, RIGHT_EYE, width, height)
        ear_avg = (ear_left + ear_right) / 2.0
        mar = _mouth_aspect_ratio(landmarks, width, height)
        yaw_proxy = _yaw_proxy(landmarks, width)
        texture_score = _face_texture_score(image, landmarks, width, height)

        return FaceMeshAnalysis(
            face_detected=True,
            ear_left=round(ear_left, 4),
            ear_right=round(ear_right, 4),
            ear_avg=round(ear_avg, 4),
            mar=round(mar, 4),
            yaw_proxy=round(yaw_proxy, 4),
            texture_score=round(texture_score, 4),
            eyes_open=ear_avg >= ear_open_min,
            mouth_open=mar >= mar_open_min,
            face_x=round(x1 + face_w / 2, 2),
            face_y=round(y1 + face_h / 2, 2),
            face_width=round(face_w, 2),
            face_height=round(face_h, 2),
        )


def _eye_aspect_ratio(landmarks, indices: tuple[int, ...], width: int, height: int) -> float:
    points = [(landmarks[i].x * width, landmarks[i].y * height) for i in indices]
    vertical_a = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    vertical_b = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    horizontal = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
    if horizontal <= 0:
        return 0.0
    return float((vertical_a + vertical_b) / (2.0 * horizontal))


def _mouth_aspect_ratio(landmarks, width: int, height: int) -> float:
    top = (landmarks[MOUTH_TOP].x * width, landmarks[MOUTH_TOP].y * height)
    bottom = (landmarks[MOUTH_BOTTOM].x * width, landmarks[MOUTH_BOTTOM].y * height)
    left = (landmarks[MOUTH_LEFT].x * width, landmarks[MOUTH_LEFT].y * height)
    right = (landmarks[MOUTH_RIGHT].x * width, landmarks[MOUTH_RIGHT].y * height)
    vertical = np.linalg.norm(np.array(top) - np.array(bottom))
    horizontal = np.linalg.norm(np.array(left) - np.array(right))
    if horizontal <= 0:
        return 0.0
    return float(vertical / horizontal)


def _yaw_proxy(landmarks, width: int) -> float:
    nose_x = landmarks[NOSE_TIP].x * width
    left_x = landmarks[LEFT_CHEEK].x * width
    right_x = landmarks[RIGHT_CHEEK].x * width
    face_width = right_x - left_x
    if face_width <= 0:
        return 0.0
    face_center = (left_x + right_x) / 2.0
    return float((nose_x - face_center) / face_width)


def _face_texture_score(
    image: np.ndarray,
    landmarks,
    width: int,
    height: int,
) -> float:
    xs = [landmarks[i].x * width for i in (LEFT_CHEEK, RIGHT_CHEEK, NOSE_TIP)]
    ys = [landmarks[i].y * height for i in (LEFT_CHEEK, RIGHT_CHEEK, NOSE_TIP)]
    pad = 12
    x1 = max(0, int(min(xs) - pad))
    y1 = max(0, int(min(ys) - pad))
    x2 = min(width, int(max(xs) + pad))
    y2 = min(height, int(max(ys) + pad))
    if x2 <= x1 or y2 <= y1:
        return 0.0

    crop = image[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())
