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
