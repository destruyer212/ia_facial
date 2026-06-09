from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.services.supabase_db import get_conn, resolve_org_id


class LivenessStore:
    def save_check(
        self,
        *,
        passed: bool,
        score: float,
        method: str,
        checks: dict,
        challenge_id: str | None = None,
        person_id: str | None = None,
        evidence_ref: str | None = None,
    ) -> str:
        check_id = str(uuid4())
        if settings.storage_backend.lower() == "supabase":
            self._save_supabase(
                check_id=check_id,
                passed=passed,
                score=score,
                method=method,
                checks=checks,
                challenge_id=challenge_id,
                person_id=person_id,
                evidence_ref=evidence_ref,
            )
        else:
            self._save_local(
                check_id=check_id,
                passed=passed,
                score=score,
                method=method,
                checks=checks,
                challenge_id=challenge_id,
                person_id=person_id,
                evidence_ref=evidence_ref,
            )
        return check_id

    def _save_local(self, **payload: object) -> None:
        path = settings.resolved_data_dir / "liveness_checks.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        records: list[dict] = []
        if path.exists():
            records = json.loads(path.read_text(encoding="utf-8"))
        payload["created_at"] = datetime.now(UTC).isoformat()
        records.append(payload)
        path.write_text(json.dumps(records[-200:], indent=2), encoding="utf-8")

    def _save_supabase(self, **payload: object) -> None:
        try:
            with get_conn() as conn:
                org_id = resolve_org_id(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into public.liveness_checks
                          (check_id, org_id, person_id, passed, score, method,
                           challenge_id, checks, evidence_ref)
                        values
                          (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (
                            payload["check_id"],
                            org_id,
                            payload.get("person_id"),
                            payload["passed"],
                            payload["score"],
                            payload["method"],
                            payload.get("challenge_id"),
                            json.dumps(payload.get("checks") or {}),
                            payload.get("evidence_ref"),
                        ),
                    )
        except Exception:
            self._save_local(**payload)


def get_liveness_store() -> LivenessStore:
    return LivenessStore()
