from pathlib import Path

import cv2

from app.schemas.face import FaceBox, FaceDetectionResponse


class OpenCVService:
    def __init__(self) -> None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(str(cascade_path))

    def detect_faces(self, image_path: Path, *, relaxed: bool = False) -> FaceDetectionResponse:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("No se pudo leer la imagen enviada.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if relaxed:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=4,
                minSize=(35, 35),
            )
        else:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

        height, width = image.shape[:2]
        boxes = [
            FaceBox(x=int(x), y=int(y), width=int(w), height=int(h))
            for (x, y, w, h) in faces
        ]
        return FaceDetectionResponse(
            image_width=int(width),
            image_height=int(height),
            face_count=len(boxes),
            faces=boxes,
        )

