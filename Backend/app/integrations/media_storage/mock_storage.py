"""Storage en memoria para tests y desarrollo sin credenciales S3."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

from app.integrations.media_storage.types import ObjectHeadResult, PresignedUrlResult


class MockMediaStorage:
    """
    Simula un bucket S3 privado en memoria.

    Las URLs firmadas son identificadores opacos; la subida real se hace vía
    ``put_object_bytes`` en tests o mediante parseo de la URL mock.
    """

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self._objects: Dict[str, dict] = {}

    def put_object_bytes(self, object_key: str, body: bytes, content_type: str) -> None:
        """Carga directa usada en tests para simular PUT del navegador."""
        self._objects[object_key] = {
            "body": body,
            "content_type": content_type,
        }

    def create_presigned_put(
        self,
        object_key: str,
        content_type: str,
        expires_seconds: int,
    ) -> PresignedUrlResult:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        url = f"mock://put/{self.bucket}/{object_key}?ct={content_type}"
        return PresignedUrlResult(url=url, expires_at=expires_at)

    def head_object(self, object_key: str) -> ObjectHeadResult | None:
        row = self._objects.get(object_key)
        if row is None:
            return None
        return ObjectHeadResult(
            content_length=len(row["body"]),
            content_type=row.get("content_type"),
        )

    def get_object_bytes(self, object_key: str) -> bytes | None:
        row = self._objects.get(object_key)
        if row is None:
            return None
        return row["body"]

    def create_presigned_get(self, object_key: str, expires_seconds: int) -> PresignedUrlResult:
        if object_key not in self._objects:
            raise FileNotFoundError(object_key)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        url = f"mock://get/{self.bucket}/{object_key}"
        return PresignedUrlResult(url=url, expires_at=expires_at)

    def delete_object(self, object_key: str) -> None:
        self._objects.pop(object_key, None)

    def ingest_from_presigned_put_url(self, upload_url: str, body: bytes) -> None:
        """Simula la subida del cliente a partir de la URL devuelta en upload-intent."""
        if not upload_url.startswith("mock://put/"):
            raise ValueError("URL de subida mock no reconocida.")
        path = upload_url.split("?", 1)[0]
        parts = path.replace("mock://put/", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError("URL mock malformada.")
        _bucket, object_key = parts
        ct = "application/octet-stream"
        if "?ct=" in upload_url:
            ct = upload_url.split("?ct=", 1)[1]
        self.put_object_bytes(object_key, body, ct)
