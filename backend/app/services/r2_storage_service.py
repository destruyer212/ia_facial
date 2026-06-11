from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


@dataclass
class UploadResult:
    key: str
    public_url: str | None


class R2StorageService:
    def __init__(self, client: BaseClient | None = None) -> None:
        self.bucket = settings.r2_bucket
        self._public_base_url = settings.r2_public_base_url.rstrip("/")
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    def upload_file(self, file_path: Path, object_key: str, content_type: str) -> UploadResult:
        self._client.upload_file(
            Filename=str(file_path),
            Bucket=self.bucket,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )
        public_url = f"{self._public_base_url}/{object_key}" if self._public_base_url else None
        return UploadResult(key=object_key, public_url=public_url)

    def verify_connection(self) -> tuple[bool, str]:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True, "R2 conectado correctamente."
        except (BotoCoreError, ClientError) as exc:
            return False, f"R2 error: {exc}"

    def delete_objects(self, object_keys: list[str]) -> int:
        keys = [key.strip() for key in object_keys if key and key.strip()]
        if not keys:
            return 0
        deleted = 0
        for index in range(0, len(keys), 1000):
            batch = keys[index : index + 1000]
            try:
                response = self._client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
                )
                deleted += len(response.get("Deleted", []))
            except (BotoCoreError, ClientError):
                continue
        return deleted
