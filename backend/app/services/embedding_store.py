import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.face import MatchCandidate, StoredFaceEmbedding, StoredFacePublic
from app.services.supabase_db import (
    ensure_person,
    get_conn,
    person_exists,
    resolve_org_id,
    update_person,
)


def sanitize_person_id(person_id: str) -> str:
    return person_id.strip().replace("/", "_").replace("\\", "_")


def portrait_api_path(person_id: str) -> str:
    return f"/api/v1/faces/portrait/{sanitize_person_id(person_id)}"


class LocalEmbeddingStore:
    """JSON storage for the desktop MVP. Replace with PostgreSQL + pgvector later."""

    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "embeddings.json"
        self.portraits_dir = data_dir / "portraits"
        self.portraits_dir.mkdir(parents=True, exist_ok=True)

    def save_embedding(
        self,
        person_id: str,
        name: str,
        model: str,
        embedding: list[float],
        email: str | None = None,
        pose_type: str = "front",
    ) -> StoredFaceEmbedding:
        person_id = person_id.strip()
        pose_type = pose_type.strip() or "front"
        records = self._load()
        records = [
            record
            for record in records
            if not (
                record.person_id == person_id
                and record.model == model
                and record.pose_type == pose_type
            )
        ]
        existing = next((record for record in records if record.person_id == person_id), None)
        stored = StoredFaceEmbedding(
            person_id=person_id,
            name=name.strip(),
            model=model,
            embedding=embedding,
            pose_type=pose_type,
            created_at=existing.created_at if existing else datetime.now(UTC),
            image_url=existing.image_url if existing and pose_type == "front" else None,
            email=(email or (existing.email if existing else None)),
            employee_code=person_id,
            is_active=existing.is_active if existing else True,
            embedding_count=0,
        )
        records.append(stored)
        self._save(records)
        count = sum(1 for record in records if record.person_id == person_id)
        stored.embedding_count = count
        return stored

    def count_person_embeddings(self, person_id: str) -> int:
        return sum(1 for record in self._load() if record.person_id == person_id.strip())

    def save_portrait(self, person_id: str, source_path: Path, pose_type: str = "front") -> str:
        person_id = person_id.strip()
        pose_type = pose_type.strip() or "front"
        filename = (
            f"{sanitize_person_id(person_id)}.jpg"
            if pose_type == "front"
            else f"{sanitize_person_id(person_id)}_{pose_type}.jpg"
        )
        dest = self.portraits_dir / filename
        shutil.copy(source_path, dest)
        image_url = (
            portrait_api_path(person_id)
            if pose_type == "front"
            else f"/api/v1/faces/portrait/{sanitize_person_id(person_id)}/{pose_type}"
        )
        if pose_type == "front":
            records = self._load()
            for record in records:
                if record.person_id == person_id:
                    record.image_url = portrait_api_path(person_id)
            self._save(records)
        return image_url

    def get_portrait_path(self, person_id: str, pose_type: str = "front") -> Path | None:
        person_id = person_id.strip()
        pose_type = pose_type.strip() or "front"
        filename = (
            f"{sanitize_person_id(person_id)}.jpg"
            if pose_type == "front"
            else f"{sanitize_person_id(person_id)}_{pose_type}.jpg"
        )
        path = self.portraits_dir / filename
        return path if path.exists() else None

    def find_best_match(
        self,
        embedding: list[float],
        threshold: float,
        model: str,
    ) -> MatchCandidate | None:
        candidates = [record for record in self._load() if record.model == model]
        best: MatchCandidate | None = None

        for record in candidates:
            if not record.is_active:
                continue
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

    def find_nearest_candidate(
        self,
        embedding: list[float],
        model: str,
    ) -> MatchCandidate | None:
        candidates = [record for record in self._load() if record.model == model]
        best: MatchCandidate | None = None

        for record in candidates:
            if not record.is_active:
                continue
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

        return best

    def list_public(self) -> list[StoredFacePublic]:
        records = self._load()
        counts: dict[str, int] = {}
        for record in records:
            counts[record.person_id] = counts.get(record.person_id, 0) + 1
        latest_by_person: dict[str, StoredFaceEmbedding] = {}
        for record in records:
            current = latest_by_person.get(record.person_id)
            if current is None or record.created_at >= current.created_at:
                latest_by_person[record.person_id] = record
        return [
            StoredFacePublic(
                person_id=record.person_id,
                name=record.name,
                model=record.model,
                created_at=record.created_at,
                image_url=record.image_url or (
                    portrait_api_path(record.person_id)
                    if self.get_portrait_path(record.person_id)
                    else None
                ),
                email=record.email,
                employee_code=record.employee_code or record.person_id,
                is_active=record.is_active,
                embedding_count=counts.get(record.person_id, 1),
            )
            for record in sorted(
                latest_by_person.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        ]

    def count(self) -> int:
        return len(self._load())

    def update_employee(
        self,
        person_id: str,
        *,
        name: str | None = None,
        email: str | None = None,
        employee_code: str | None = None,
        is_active: bool | None = None,
    ) -> StoredFacePublic:
        person_id = person_id.strip()
        records = self._load()
        matched = [record for record in records if record.person_id == person_id]
        if not matched:
            raise LookupError(f"No existe empleado con person_id='{person_id}'.")

        for record in matched:
            if name is not None:
                record.name = name.strip()
            if email is not None:
                record.email = email.strip() or None
            if employee_code is not None:
                record.employee_code = employee_code.strip() or person_id
            if is_active is not None:
                record.is_active = is_active

        self._save(records)
        public = next(
            (face for face in self.list_public() if face.person_id == person_id),
            None,
        )
        if public is None:
            raise LookupError(f"No existe empleado con person_id='{person_id}'.")
        return public

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


class SupabaseEmbeddingStore:
    def __init__(self) -> None:
        portraits_dir = settings.resolved_data_dir / "portraits"
        portraits_dir.mkdir(parents=True, exist_ok=True)
        self.portraits_dir = portraits_dir

    def save_embedding(
        self,
        person_id: str,
        name: str,
        model: str,
        embedding: list[float],
        email: str | None = None,
        pose_type: str = "front",
    ) -> StoredFaceEmbedding:
        person_id = person_id.strip()
        name = name.strip()
        pose_type = pose_type.strip() or "front"
        embedding_literal = "[" + ",".join(str(float(v)) for v in embedding) + "]"
        metadata = json.dumps({"pose_type": pose_type})
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            ensure_person(
                conn,
                org_id=org_id,
                person_id=person_id,
                full_name=name,
                email=email,
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from public.face_embeddings
                    where person_id = %s
                      and model = %s
                      and coalesce(metadata->>'pose_type', 'front') = %s
                    """,
                    (person_id, model, pose_type),
                )
                cur.execute(
                    """
                    insert into public.face_embeddings
                      (org_id, person_id, model, embedding, threshold, metadata)
                    values
                      (%s, %s, %s, %s::vector, %s, %s::jsonb)
                    """,
                    (
                        org_id,
                        person_id,
                        model,
                        embedding_literal,
                        settings.face_match_threshold,
                        metadata,
                    ),
                )
        return StoredFaceEmbedding(
            person_id=person_id,
            name=name,
            model=model,
            embedding=embedding,
            pose_type=pose_type,
            created_at=datetime.now(UTC),
            embedding_count=self.count_person_embeddings(person_id),
        )

    def count_person_embeddings(self, person_id: str) -> int:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select count(*)
                    from public.face_embeddings
                    where org_id = %s and person_id = %s
                    """,
                    (org_id, person_id.strip()),
                )
                return int(cur.fetchone()[0])

    def find_best_match(
        self,
        embedding: list[float],
        threshold: float,
        model: str,
    ) -> MatchCandidate | None:
        embedding_literal = "[" + ",".join(str(float(v)) for v in embedding) + "]"
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select person_id, full_name, model, distance, confidence
                    from public.match_face_embeddings(
                      %s::uuid,
                      %s::text,
                      %s::vector(512),
                      %s::real,
                      %s::integer
                    )
                    """,
                    (org_id, model, embedding_literal, float(threshold), 5),
                )
                for row in cur.fetchall():
                    return MatchCandidate(
                        person_id=row[0],
                        name=row[1],
                        model=row[2],
                        distance=round(float(row[3]), 6),
                        confidence=round(float(row[4]), 6),
                    )
                return self._find_nearest_candidate_fallback(
                    cur, org_id=org_id, model=model, embedding_literal=embedding_literal
                )

    def find_nearest_candidate(
        self,
        embedding: list[float],
        model: str,
    ) -> MatchCandidate | None:
        embedding_literal = "[" + ",".join(str(float(v)) for v in embedding) + "]"
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                return self._find_nearest_candidate_fallback(
                    cur, org_id=org_id, model=model, embedding_literal=embedding_literal
                )

    @staticmethod
    def _find_nearest_candidate_fallback(
        cur,
        *,
        org_id,
        model: str,
        embedding_literal: str,
    ) -> MatchCandidate | None:
        cur.execute(
            """
            select
              e.person_id,
              p.full_name,
              e.model,
              (e.embedding <=> %s::vector(512))::real as distance,
              greatest(0, least(1, 1 - (e.embedding <=> %s::vector(512))))::real
                as confidence
            from public.face_embeddings e
            join public.persons p
              on p.person_id = e.person_id and p.org_id = e.org_id
            where e.org_id = %s
              and e.model = %s
              and p.is_active = true
            order by e.embedding <=> %s::vector(512)
            limit 1
            """,
            (embedding_literal, embedding_literal, org_id, model, embedding_literal),
        )
        row = cur.fetchone()
        if not row:
            return None
        return MatchCandidate(
            person_id=row[0],
            name=row[1],
            model=row[2],
            distance=round(float(row[3]), 6),
            confidence=round(float(row[4]), 6),
        )

    def save_portrait(self, person_id: str, source_path: Path, pose_type: str = "front") -> str:
        person_id = person_id.strip()
        pose_type = pose_type.strip() or "front"
        filename = (
            f"{sanitize_person_id(person_id)}.jpg"
            if pose_type == "front"
            else f"{sanitize_person_id(person_id)}_{pose_type}.jpg"
        )
        dest = self.portraits_dir / filename
        shutil.copy(source_path, dest)
        return (
            portrait_api_path(person_id)
            if pose_type == "front"
            else f"/api/v1/faces/portrait/{sanitize_person_id(person_id)}/{pose_type}"
        )

    def get_portrait_path(self, person_id: str, pose_type: str = "front") -> Path | None:
        person_id = person_id.strip()
        pose_type = pose_type.strip() or "front"
        filename = (
            f"{sanitize_person_id(person_id)}.jpg"
            if pose_type == "front"
            else f"{sanitize_person_id(person_id)}_{pose_type}.jpg"
        )
        path = self.portraits_dir / filename
        return path if path.exists() else None

    def list_public(self) -> list[StoredFacePublic]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select distinct on (fe.person_id)
                      fe.person_id,
                      p.full_name,
                      p.email,
                      p.employee_code,
                      p.is_active,
                      fe.model,
                      fe.created_at,
                      fa.public_url,
                      (
                        select count(*)
                        from public.face_embeddings fe2
                        where fe2.org_id = fe.org_id and fe2.person_id = fe.person_id
                      ) as embedding_count
                    from public.face_embeddings fe
                    join public.persons p on p.person_id = fe.person_id
                    left join public.face_assets fa on fa.person_id = fe.person_id
                    where fe.org_id = %s
                    order by fe.person_id, fa.created_at desc nulls last, fe.created_at desc
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()
        faces: list[StoredFacePublic] = []
        for row in rows:
            person_id = row[0]
            public_url = row[7]
            embedding_count = int(row[8] or 1)
            local_path = self.get_portrait_path(person_id)
            image_url = public_url or (portrait_api_path(person_id) if local_path else None)
            faces.append(
                StoredFacePublic(
                    person_id=person_id,
                    name=row[1],
                    email=row[2],
                    employee_code=row[3] or person_id,
                    is_active=bool(row[4]),
                    model=row[5],
                    created_at=row[6],
                    image_url=image_url,
                    embedding_count=embedding_count,
                )
            )
        return sorted(faces, key=lambda item: item.created_at, reverse=True)

    def count(self) -> int:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "select count(*) from public.face_embeddings where org_id = %s",
                    (org_id,),
                )
                return int(cur.fetchone()[0])

    def update_employee(
        self,
        person_id: str,
        *,
        name: str | None = None,
        email: str | None = None,
        employee_code: str | None = None,
        is_active: bool | None = None,
    ) -> StoredFacePublic:
        person_id = person_id.strip()
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            if not person_exists(conn, org_id=org_id, person_id=person_id):
                raise LookupError(f"No existe empleado con person_id='{person_id}'.")
            updated = update_person(
                conn,
                org_id=org_id,
                person_id=person_id,
                full_name=name,
                email=email,
                employee_code=employee_code,
                is_active=is_active,
            )
            if not updated and all(
                value is None for value in (name, email, employee_code, is_active)
            ):
                raise ValueError("No se enviaron campos para actualizar.")

        public = next(
            (face for face in self.list_public() if face.person_id == person_id),
            None,
        )
        if public is None:
            raise LookupError(f"No existe empleado con person_id='{person_id}'.")
        return public


def get_embedding_store():
    if settings.storage_backend.lower() == "supabase":
        return SupabaseEmbeddingStore()
    return LocalEmbeddingStore()

