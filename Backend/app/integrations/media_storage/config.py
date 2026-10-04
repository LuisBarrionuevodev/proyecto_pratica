"""Configuración de Media Storage desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class MediaStorageConfig:
    """Parámetros de storage y límites de carga."""

    provider: str
    bucket: str
    endpoint: str | None
    region: str
    access_key_id: str | None
    secret_access_key: str | None
    presigned_ttl_seconds: int
    max_image_bytes: int
    max_document_bytes: int
    max_acta_documentacion_per_ruta_item: int
    max_foto_inspeccion_per_ruta_item: int


def load_media_storage_config() -> MediaStorageConfig:
    """
    Carga configuración de media desde el entorno.

    Retorno:
        MediaStorageConfig con defaults de desarrollo cuando faltan variables.

    Errores:
        ValueError: enteros inválidos en variables numéricas.
    """
    return MediaStorageConfig(
        provider=(os.getenv("MEDIA_STORAGE_PROVIDER") or "mock").strip().lower(),
        bucket=(os.getenv("MEDIA_S3_BUCKET") or "digitaliza-media-dev").strip(),
        endpoint=(os.getenv("MEDIA_S3_ENDPOINT") or "").strip() or None,
        region=(os.getenv("MEDIA_S3_REGION") or "auto").strip(),
        access_key_id=(os.getenv("MEDIA_S3_ACCESS_KEY_ID") or "").strip() or None,
        secret_access_key=(os.getenv("MEDIA_S3_SECRET_ACCESS_KEY") or "").strip() or None,
        presigned_ttl_seconds=_int_env("MEDIA_PRESIGNED_URL_TTL_SECONDS", 600),
        max_image_bytes=_int_env("MEDIA_MAX_IMAGE_BYTES", 10_485_760),
        max_document_bytes=_int_env("MEDIA_MAX_DOCUMENT_BYTES", 15_728_640),
        max_acta_documentacion_per_ruta_item=_int_env(
            "MEDIA_MAX_ACTA_DOCUMENTACION_PER_RUTA_ITEM", 8
        ),
        max_foto_inspeccion_per_ruta_item=_int_env(
            "MEDIA_MAX_FOTO_INSPECCION_PER_RUTA_ITEM", 12
        ),
    )
