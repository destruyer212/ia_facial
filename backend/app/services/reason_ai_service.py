import json
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.attendance import ReasonAnalysis


class ReasonAIService:
    def analyze_reason(self, reason: str) -> ReasonAnalysis:
        clean_reason = reason.strip()
        if settings.ollama_enabled:
            try:
                return self._analyze_with_ollama(clean_reason)
            except Exception:
                return self._analyze_with_rules(clean_reason, provider="rules-fallback")
        return self._analyze_with_rules(clean_reason, provider="rules")

    def _analyze_with_ollama(self, reason: str) -> ReasonAnalysis:
        prompt = (
            "Analiza este motivo de salida temprana laboral. "
            "Devuelve solo JSON con campos: is_valid boolean, category string, "
            "confidence number 0-1, risk_score number 0-1, explanation string. "
            "Criterio: salud, emergencia familiar, autorizacion formal o seguridad "
            "pueden ser validos; comodidad, cansancio, ocio o motivos vagos no. "
            f"Motivo: {reason}"
        )
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            body = response.json()

        parsed = json.loads(body.get("response", "{}"))
        return ReasonAnalysis(
            is_valid=bool(parsed.get("is_valid", False)),
            category=str(parsed.get("category", "unknown")),
            confidence=clamp_float(parsed.get("confidence", 0.5)),
            risk_score=clamp_float(parsed.get("risk_score", 0.5)),
            explanation=str(parsed.get("explanation", "Analisis generado por Ollama.")),
            provider=f"ollama:{settings.ollama_model}",
        )

    @staticmethod
    def _analyze_with_rules(reason: str, provider: str) -> ReasonAnalysis:
        lowered = reason.lower()
        if len(lowered) < 8:
            return ReasonAnalysis(
                is_valid=False,
                category="insufficient_reason",
                confidence=0.9,
                risk_score=0.85,
                explanation="El motivo es demasiado corto o ambiguo para justificar salida temprana.",
                provider=provider,
            )

        valid_keywords = {
            "salud": "health",
            "medico": "health",
            "medica": "health",
            "hospital": "health",
            "emergencia": "emergency",
            "accidente": "emergency",
            "familiar": "family_emergency",
            "autorizado": "authorized",
            "permiso": "authorized",
            "supervisor": "authorized",
            "seguridad": "safety",
        }
        invalid_keywords = {
            "cansado": "convenience",
            "aburrido": "convenience",
            "fiesta": "personal_leisure",
            "partido": "personal_leisure",
            "quiero irme": "convenience",
            "no hay trabajo": "low_workload",
        }

        for keyword, category in invalid_keywords.items():
            if keyword in lowered:
                return ReasonAnalysis(
                    is_valid=False,
                    category=category,
                    confidence=0.82,
                    risk_score=0.8,
                    explanation="El motivo parece personal, vago o no justifica incumplir horario.",
                    provider=provider,
                )

        for keyword, category in valid_keywords.items():
            if keyword in lowered:
                return ReasonAnalysis(
                    is_valid=True,
                    category=category,
                    confidence=0.76,
                    risk_score=0.25,
                    explanation="El motivo contiene senales razonables para excepcion operativa.",
                    provider=provider,
                )

        return ReasonAnalysis(
            is_valid=False,
            category="unverified_reason",
            confidence=0.65,
            risk_score=0.7,
            explanation="El motivo no contiene evidencia suficiente para aprobar la salida temprana.",
            provider=provider,
        )


def clamp_float(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))
