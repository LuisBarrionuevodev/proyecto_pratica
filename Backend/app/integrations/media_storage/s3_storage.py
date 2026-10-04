"""Adaptador S3-compatible (Railway Storage Buckets)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import boto3
from botocore.client import Config

from app.integrations.media_storage.config import MediaStorageConfig
from app.integrations.media_storage.types import ObjectHeadResult, PresignedUrlResult


class RailwayS3MediaStorage:
    """
    Cliente S3 para storage privado Railway.

    Parámetros:
        config: credenciales y bucket desde entorno.
    """

    def __init__(self, config: MediaStorageConfig) -> None:
        if not config.access_key_id or not config.secret_access_key:
            raise ValueError("MEDIA_S3_ACCESS_KEY_ID y MEDIA_S3_SECRET_ACCESS_KEY son obligatorios.")
        if not config.endpoint:
            raise ValueError("MEDIA_S3_ENDPOINT es obligatorio para railway_s3.")
        self._config = config
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    def create_presigned_put(
        self,
        object_key: str,
        content_type: str,
        expires_seconds: int,
    ) -> PresignedUrlResult:
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._config.bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_seconds,
        )
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        return PresignedUrlResult(url=url, expires_at=expires_at)

    def head_object(self, object_key: str) -> ObjectHeadResult | None:
        from botocore.exceptions import ClientError

        try:
            resp = self._client.head_object(Bucket=self._config.bucket, Key=object_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound", "403"):
                return None
            raise
        return ObjectHeadResult(
            content_length=int(resp.get("ContentLength") or 0),
            content_type=resp.get("ContentType"),
        )

    def get_object_bytes(self, object_key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._config.bucket, Key=object_key)
        except Exception:
            return None
        return resp["Body"].read()

    def create_presigned_get(self, object_key: str, expires_seconds: int) -> PresignedUrlResult:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._config.bucket, "Key": object_key},
            ExpiresIn=expires_seconds,
        )
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        return PresignedUrlResult(url=url, expires_at=expires_at)

    def delete_object(self, object_key: str) -> None:
        self._client.delete_object(Bucket=self._config.bucket, Key=object_key)
