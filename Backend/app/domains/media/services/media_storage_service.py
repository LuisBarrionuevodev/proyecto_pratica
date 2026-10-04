"""Fachada de storage: URLs firmadas y operaciones sobre el bucket."""

from __future__ import annotations

from app.domains.media.constants import STORAGE_PROVIDER_RAILWAY
from app.domains.media.utils.object_key import build_object_key
from app.integrations.media_storage.config import load_media_storage_config
from app.integrations.media_storage.factory import get_media_storage
from app.integrations.media_storage.types import ObjectHeadResult, PresignedUrlResult


class MediaStorageService:
    """
    Orquesta object_key y operaciones S3/mock sin exponer credenciales.

    Métodos delegan en el adaptador configurado por ``MEDIA_STORAGE_PROVIDER``.
    """

    def __init__(self) -> None:
        self._config = load_media_storage_config()
        self._storage = get_media_storage()

    @property
    def bucket(self) -> str:
        return self._config.bucket

    @property
    def storage_provider(self) -> str:
        return STORAGE_PROVIDER_RAILWAY

    @property
    def presigned_ttl_seconds(self) -> int:
        return self._config.presigned_ttl_seconds

    def generate_object_key(
        self,
        *,
        ruta_item_id: int,
        categoria: str,
        content_type: str,
    ) -> str:
        """Genera object_key seguro para el ítem y categoría."""
        return build_object_key(
            ruta_item_id=ruta_item_id,
            categoria=categoria,
            content_type=content_type,
        )

    def create_presigned_put(
        self,
        object_key: str,
        content_type: str,
    ) -> PresignedUrlResult:
        """URL firmada PUT para subida directa del navegador."""
        return self._storage.create_presigned_put(
            object_key,
            content_type,
            self._config.presigned_ttl_seconds,
        )

    def head_object(self, object_key: str) -> ObjectHeadResult | None:
        """HEAD del objeto en el bucket."""
        return self._storage.head_object(object_key)

    def get_object_bytes(self, object_key: str) -> bytes | None:
        """Descarga bytes del objeto (confirmación / hash)."""
        return self._storage.get_object_bytes(object_key)

    def create_presigned_get(self, object_key: str) -> PresignedUrlResult:
        """URL firmada GET para descarga autorizada."""
        return self._storage.create_presigned_get(
            object_key,
            self._config.presigned_ttl_seconds,
        )

    def delete_object(self, object_key: str) -> None:
        """Elimina objeto del bucket (rechazo / cleanup)."""
        self._storage.delete_object(object_key)
