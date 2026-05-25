import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.similarity import cosine_distance


@dataclass(frozen=True)
class EmployeeEmbedding:
    person_id: str
    name: str
    model: str
    embedding: np.ndarray


@dataclass(frozen=True)
class MatchResult:
    person_id: str
    name: str
    distance: float
    confidence: float


class EmbeddingCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.records: list[EmployeeEmbedding] = []

    def load(self) -> None:
        if not self.path.exists():
            self.records = []
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = [
            EmployeeEmbedding(
                person_id=item["person_id"],
                name=item["name"],
                model=item.get("model", "unknown"),
                embedding=np.asarray(item["embedding"], dtype=np.float32),
            )
            for item in payload
        ]

    def find_best_match(
        self,
        embedding: np.ndarray,
        threshold: float,
    ) -> MatchResult | None:
        best: MatchResult | None = None
        for record in self.records:
            distance = cosine_distance(embedding, record.embedding)
            confidence = max(0.0, min(1.0, 1.0 - distance))
            candidate = MatchResult(
                person_id=record.person_id,
                name=record.name,
                distance=round(distance, 6),
                confidence=round(confidence, 6),
            )
            if best is None or candidate.distance < best.distance:
                best = candidate

        if best is None or best.distance > threshold:
            return None
        return best

    def count(self) -> int:
        return len(self.records)

