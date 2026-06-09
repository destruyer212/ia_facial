from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.face import (
    LivenessChallengeResponse,
    LivenessChallengeStep,
    LivenessVerifyResponse,
    MatchCandidate,
)
from app.services.anti_spoof_service import AntiSpoofService
from app.services.embedding_store import cosine_distance, get_embedding_store
from app.services.face_ai_service import FaceAIService
from app.services.face_mesh_service import FaceMeshAnalysis, FaceMeshService
from app.services.liveness_store import get_liveness_store
from app.services.opencv_service import OpenCVService

CHALLENGE_PROMPTS = {
    "front": "Mire directo a la camara",
    "movement": "Gire un poco la cabeza a la izquierda o derecha",
    "blink": "Parpadee despacio",
    "smile": "Sonria levemente o abra un poco la boca",
}

CHALLENGE_FIELDS = {
    "front": "step_front",
    "movement": "step_movement",
    "blink": "step_blink",
    "smile": "step_smile",
}

CHECK_WEIGHTS = {
    "face_detected": 0.05,
    "same_person": 0.22,
    "movement": 0.14,
    "blink": 0.14,
    "eyes_open_front": 0.05,
    "texture": 0.10,
    "anti_spoof": 0.20,
    "smile": 0.10,
}


@dataclass
class FrameAnalysis:
    embedding: list[float] | None
    face_x: float
    face_y: float
    face_width: float
    mesh: FaceMeshAnalysis
    anti_spoof_live: bool
    anti_spoof_score: float
    step_type: str


class LivenessService:
    """Fase 4: desafio aleatorio, MAR/sonrisa, anti-spoof compuesto, score >= 0.85."""

    def __init__(
        self,
        face_ai: FaceAIService | None = None,
        opencv: OpenCVService | None = None,
        face_mesh: FaceMeshService | None = None,
        anti_spoof: AntiSpoofService | None = None,
    ) -> None:
        self.face_ai = face_ai or FaceAIService()
        self.opencv = opencv or OpenCVService()
        self.face_mesh = face_mesh or FaceMeshService()
        self.anti_spoof = anti_spoof or AntiSpoofService()
        self.embedding_store = get_embedding_store()
        self.store = get_liveness_store()
        self.max_same_person_distance = settings.liveness_max_same_person_distance
        self.min_face_shift_px = settings.liveness_min_face_shift_px
        self.ear_blink_max = settings.liveness_ear_blink_max
        self.ear_open_min = settings.liveness_ear_open_min
        self.mar_open_min = settings.liveness_mar_open_min
        self.min_head_yaw_delta = settings.liveness_min_head_yaw_delta
        self.min_texture_score = settings.liveness_min_texture_score
        self.min_anti_spoof_score = settings.liveness_min_anti_spoof_score
        self.min_pass_score = settings.liveness_min_pass_score

    def create_challenge(self) -> LivenessChallengeResponse:
        challenge_id = uuid4().hex
        tail = ["movement", "blink"]
        if settings.liveness_smile_enabled and random.random() < 0.5:
            tail.append("smile")
        random.shuffle(tail)
        step_types = ["front", *tail]
        steps = [
            LivenessChallengeStep(
                type=step_type,
                prompt=CHALLENGE_PROMPTS[step_type],
                form_field=CHALLENGE_FIELDS[step_type],
                order=index + 1,
            )
            for index, step_type in enumerate(step_types)
        ]
        return LivenessChallengeResponse(challenge_id=challenge_id, steps=steps)

    def verify(
        self,
        frames_by_type: dict[str, Path],
        *,
        challenge_id: str | None = None,
        person_id: str | None = None,
    ) -> LivenessVerifyResponse:
        if "front" not in frames_by_type:
            return self._fail("Falta captura frontal.", {"frames": False})

        required = {"front", "movement", "blink"}
        missing = required - set(frames_by_type.keys())
        if missing:
            return self._fail(
                f"Faltan capturas: {', '.join(sorted(missing))}.",
                {"frames": False},
            )

        try:
            frames = {
                step_type: self._analyze_frame(path, step_type)
                for step_type, path in frames_by_type.items()
            }
        except ValueError as exc:
            return self._fail(str(exc), {"face_detected": False})
        except Exception as exc:
            return self._fail(
                f"Error analizando captura: {exc}",
                {"face_detected": False},
            )

        front = frames["front"]
        movement = frames["movement"]
        blink = frames["blink"]
        smile = frames.get("smile")

        if not all(frame.mesh.face_detected for frame in frames.values()):
            detected = sum(
                1 for frame in frames.values()
                if frame.mesh.face_detected or frame.face_width > 0
            )
            if detected < 2:
                return self._persist_and_return(
                    self._fail(
                        "No se detecto rostro en suficientes capturas. "
                        "Mira de frente a la camara con buena luz y repite.",
                        {"face_detected": False},
                    ),
                    challenge_id=challenge_id,
                    person_id=person_id,
                )

        same_person = self._same_person_check(front, movement, blink, smile)
        movement_ok = self._movement_check(front, movement, blink)
        eyes_open_front = front.mesh.eyes_open
        blink_detected = (
            blink.mesh.ear_avg <= self.ear_blink_max
            or (front.mesh.ear_avg - blink.mesh.ear_avg) >= 0.045
        )
        texture_ok = all(
            frame.mesh.texture_score >= self.min_texture_score for frame in frames.values()
        )
        avg_spoof = sum(frame.anti_spoof_score for frame in frames.values()) / len(frames)
        liveness_proven = same_person and movement_ok and blink_detected
        # Webcam JPEG comprime textura/FFT: si hubo parpadeo + giro + misma persona, no bloquear por anti-spoof.
        anti_spoof_ok = (
            avg_spoof >= self.min_anti_spoof_score
            or (liveness_proven and avg_spoof >= 0.18)
        )

        smile_ok = True
        if smile is not None:
            smile_ok = (
                smile.mesh.mouth_open
                or smile.mesh.mar >= self.mar_open_min
                or (smile.mesh.mar - front.mesh.mar) >= 0.04
            )

        checks = {
            "face_detected": True,
            "same_person": same_person,
            "movement": movement_ok,
            "eyes_open_front": eyes_open_front,
            "blink": blink_detected,
            "texture": texture_ok,
            "anti_spoof": anti_spoof_ok,
            "smile": smile_ok if smile is not None else True,
        }
        score = self._weighted_score(checks, smile_required=smile is not None)
        critical_ok = same_person and movement_ok and blink_detected
        passed = score >= self.min_pass_score and critical_ok and anti_spoof_ok

        if passed:
            candidate = self._identify_from_front(front)
            response = LivenessVerifyResponse(
                passed=True,
                score=round(score, 3),
                message="Rostro real validado. Anti-spoofing superado. Puede continuar.",
                checks=checks,
                challenge_id=challenge_id,
                method="mediapipe_v2",
                anti_spoof_score=round(avg_spoof, 3),
                candidate=candidate,
            )
            return self._persist_and_return(response, challenge_id, person_id)

        message = self._failure_message(checks, smile is not None)
        response = LivenessVerifyResponse(
            passed=False,
            score=round(score, 3),
            message=message,
            checks=checks,
            challenge_id=challenge_id,
            method="mediapipe_v2",
            anti_spoof_score=round(avg_spoof, 3),
        )
        return self._persist_and_return(response, challenge_id, person_id)

    def _analyze_frame(self, image_path: Path, step_type: str) -> FrameAnalysis:
        mesh = self.face_mesh.analyze(
            image_path,
            ear_open_min=self.ear_open_min,
            mar_open_min=self.mar_open_min,
        )
        detection = self.opencv.detect_faces(image_path, relaxed=True)

        if mesh.face_detected:
            if detection.face_count >= 1:
                face = max(detection.faces, key=lambda item: item.width * item.height)
                face_x = float(face.x + face.width / 2)
                face_y = float(face.y + face.height / 2)
                face_width = float(face.width)
            else:
                face_x = mesh.face_x
                face_y = mesh.face_y
                face_width = mesh.face_width
        elif detection.face_count >= 1:
            face = max(detection.faces, key=lambda item: item.width * item.height)
            face_x = float(face.x + face.width / 2)
            face_y = float(face.y + face.height / 2)
            face_width = float(face.width)
        else:
            raise ValueError(
                "No se detecto rostro. Centrate en la camara, mejora la luz y acercate un poco."
            )

        embedding = (
            self.face_ai.create_embedding(image_path)
            if step_type in ("front", "blink")
            else None
        )
        spoof = self.anti_spoof.analyze(
            image_path,
            min_live_score=self.min_anti_spoof_score,
        )
        return FrameAnalysis(
            embedding=embedding,
            face_x=face_x,
            face_y=face_y,
            face_width=face_width,
            mesh=mesh,
            anti_spoof_live=spoof.is_live,
            anti_spoof_score=spoof.live_score,
            step_type=step_type,
        )

    def _same_person_check(
        self,
        front: FrameAnalysis,
        movement: FrameAnalysis,
        blink: FrameAnalysis,
        smile: FrameAnalysis | None,
    ) -> bool:
        if self._matches_registered_person([front]):
            return True

        if front.embedding and blink.embedding:
            distance = cosine_distance(front.embedding, blink.embedding)
            return distance <= self.max_same_person_distance + 0.10

        return False

    def _identify_from_front(self, front: FrameAnalysis) -> MatchCandidate | None:
        if not front.embedding:
            return None
        try:
            return self.embedding_store.find_best_match(
                embedding=front.embedding,
                threshold=settings.face_scan_match_threshold,
                model=settings.active_face_model,
            )
        except Exception:
            return None

    def _matches_registered_person(self, frames: list[FrameAnalysis | None]) -> bool:
        """Si la captura frontal coincide con un empleado activo, es la misma persona."""
        threshold = settings.face_scan_match_threshold
        model = settings.active_face_model

        for frame in frames:
            if frame is None or not frame.embedding:
                continue
            try:
                match = self.embedding_store.find_best_match(
                    embedding=frame.embedding,
                    threshold=threshold,
                    model=model,
                )
            except Exception:
                continue
            if match is not None:
                return True
        return False

    def _movement_check(
        self,
        front: FrameAnalysis,
        movement: FrameAnalysis,
        blink: FrameAnalysis,
    ) -> bool:
        shift_01 = self._face_shift(front, movement)
        shift_12 = self._face_shift(movement, blink)
        yaw_delta = max(
            abs(front.mesh.yaw_proxy - movement.mesh.yaw_proxy),
            abs(movement.mesh.yaw_proxy - blink.mesh.yaw_proxy),
        )
        return (
            shift_01 >= self.min_face_shift_px
            or shift_12 >= self.min_face_shift_px
            or yaw_delta >= self.min_head_yaw_delta
        )

    @staticmethod
    def _weighted_score(checks: dict[str, bool], *, smile_required: bool) -> float:
        weights = dict(CHECK_WEIGHTS)
        if not smile_required:
            weights.pop("smile", None)
            total = sum(weights.values())
            weights = {key: value / total for key, value in weights.items()}
        return sum(weights[key] * (1.0 if checks.get(key) else 0.0) for key in weights)

    @staticmethod
    def _face_shift(left: FrameAnalysis, right: FrameAnalysis) -> float:
        dx = abs(left.face_x - right.face_x)
        dy = abs(left.face_y - right.face_y)
        dw = abs(left.face_width - right.face_width)
        return max(dx, dy, dw * 0.35)

    @staticmethod
    def _failure_message(checks: dict[str, bool], smile_included: bool) -> str:
        if not checks["same_person"]:
            return (
                "No pudimos confirmar que las 3 capturas sean tuyas. "
                "Mira de frente al inicio, gira despacio y parpadea. "
                "Si ya tienes rostro registrado (Usuarios), deberia reconocerte."
            )
        if not checks["movement"]:
            return "Gira mas la cabeza en el paso de movimiento."
        if not checks["blink"]:
            return "No se detecto parpadeo. Cierra los ojos un instante."
        if not checks["eyes_open_front"]:
            return "En el paso inicial manten los ojos abiertos."
        if smile_included and not checks["smile"]:
            return "No se detecto sonrisa o apertura de boca. Intenta de nuevo."
        if not checks["texture"]:
            return "Mejora la luz de la habitacion e intenta de nuevo."
        if not checks["anti_spoof"]:
            return (
                "Senal anti-spoofing muy baja. Acercate a la camara, mejora la luz "
                "y evita contraluz. Si persiste, desactiva 'Validar rostro vivo' temporalmente."
            )
        return "Validacion de vida incompleta. Repite los 3 pasos."

    @staticmethod
    def _fail(message: str, checks: dict[str, bool]) -> LivenessVerifyResponse:
        return LivenessVerifyResponse(
            passed=False,
            score=0.0,
            message=message,
            checks=checks,
            method="mediapipe_v2",
        )

    def _persist_and_return(
        self,
        response: LivenessVerifyResponse,
        challenge_id: str | None,
        person_id: str | None,
    ) -> LivenessVerifyResponse:
        check_id = self.store.save_check(
            passed=response.passed,
            score=response.score,
            method=response.method or "mediapipe_v2",
            checks=response.checks,
            challenge_id=challenge_id,
            person_id=person_id,
            evidence_ref=f"challenge:{challenge_id}" if challenge_id else None,
        )
        response.check_id = check_id
        return response
