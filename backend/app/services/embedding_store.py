import json
import math
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.face import MatchCandidate, StoredFaceEmbedding, StoredFacePublic


class LocalEmbeddingStore:
    """JSON storage for the desktop MVP. Replace with PostgreSQL + pgvector later."""

    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "embeddings.json"

    def save_embedding(
        self,
        person_id: str,
        name: str,
        model: str,
        embedding: list[float],
    ) -> StoredFaceEmbedding:
        records = self._load()
        records = [
            record
            for record in records
            if not (record.person_id == person_id and record.model == model)
        ]
        stored = StoredFaceEmbedding(
            person_id=person_id.strip(),
            name=name.strip(),
            model=model,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
        records.append(stored)
        self._save(records)
        return stored

    def find_best_match(
        self,
        embedding: list[float],
        threshold: float,
        model: str,
    ) -> MatchCandidate | None:
        candidates = [record for record in self._load() if record.model == model]
        best: MatchCandidate | None = None

        for record in candidates:
            distance = cosine_distance(embedding, record.embedding)
            confidence = max(0.0, min(1.0, 1.0 - distance))
            candidate = MatchCandidate(
                person_id=record.person_id,
                name=record.name,
                model=record.model,
                distance=round(distance, 6),
                confidence=round(confidence, 6),
            )
            if best is None or candidate.distance < best.distance:
                best = candidate

        if best is None or best.distance > threshold:
            return None
        return best

    def list_public(self) -> list[StoredFacePublic]:
        return [
            StoredFacePublic(
                person_id=record.person_id,
                name=record.name,
                model=record.model,
                created_at=record.created_at,
            )
            for record in self._load()
        ]

    def count(self) -> int:
        return len(self._load())

    def _load(self) -> list[StoredFaceEmbedding]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [StoredFaceEmbedding(**item) for item in payload]

    def _save(self, records: list[StoredFaceEmbedding]) -> None:
        payload = [record.model_dump(mode="json") for record in records]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cosine_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Los embeddings no tienen la misma dimension.")

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 1.0
    similarity = dot / (norm_left * norm_right)
    return 1.0 - similarity

