"""Factory del adaptador de storage (mock vs Railway S3)."""

from __future__ import annotations

from typing import Union

from app.integrations.media_storage.config import MediaStorageConfig, load_media_storage_config
from app.integrations.media_storage.mock_storage import MockMediaStorage
from app.integrations.media_storage.s3_storage import RailwayS3MediaStorage

MediaStorageBackend = Union[MockMediaStorage, RailwayS3MediaStorage]

_instance: MediaStorageBackend | None = None


def get_media_storage(config: MediaStorageConfig | None = None) -> MediaStorageBackend:
    """
    Devuelve singleton del backend de storage.

    Parámetros:
        config: opcional; si se omite se lee del entorno.

    Retorno:
        MockMediaStorage o RailwayS3MediaStorage según ``MEDIA_STORAGE_PROVIDER``.
    """
    global _instance
    cfg = config or load_media_storage_config()
    if _instance is not None:
        return _instance
    if cfg.provider in ("mock", "test"):
        backend: MediaStorageBackend = MockMediaStorage(cfg.bucket)
    elif cfg.provider == "railway_s3":
        backend = RailwayS3MediaStorage(cfg)
    else:
        raise ValueError(f"MEDIA_STORAGE_PROVIDER no soportado: {cfg.provider}")
    _instance = backend
    return backend


def reset_media_storage_singleton() -> None:
    """Limpia el singleton (tests)."""
    global _instance
    _instance = None
