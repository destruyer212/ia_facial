import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


class AttendanceSyncClient:
    def __init__(self, api_base_url: str, pending_path: Path) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.pending_path = pending_path
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)

    def send_attendance_event(self, payload: dict[str, Any]) -> bool:
        payload = {
            **payload,
            "captured_at": payload.get("captured_at") or datetime.now(UTC).isoformat(),
        }
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/attendance/events",
                json=payload,
                timeout=2.0,
            )
            response.raise_for_status()
            return True
        except requests.RequestException:
            self.enqueue(payload)
            return False

    def enqueue(self, payload: dict[str, Any]) -> None:
        pending = self._load_pending()
        pending.append(payload)
        self.pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")

    def flush_pending(self) -> int:
        pending = self._load_pending()
        if not pending:
            return 0

        remaining: list[dict[str, Any]] = []
        sent = 0
        for payload in pending:
            try:
                response = requests.post(
                    f"{self.api_base_url}/api/v1/attendance/events",
                    json=payload,
                    timeout=2.0,
                )
                response.raise_for_status()
                sent += 1
            except requests.RequestException:
                remaining.append(payload)

        self.pending_path.write_text(json.dumps(remaining, indent=2), encoding="utf-8")
        return sent

    def _load_pending(self) -> list[dict[str, Any]]:
        if not self.pending_path.exists():
            return []
        return json.loads(self.pending_path.read_text(encoding="utf-8"))

