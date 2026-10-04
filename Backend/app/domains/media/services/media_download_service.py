"""Caso de uso: URL firmada de descarga para archivos READY."""

from __future__ import annotations

from app.domains.media.schemas.media_schemas import DownloadUrlOut
from app.domains.media.services.media_access_service import get_archivo_link_for_access
from app.domains.media.services.media_storage_service import MediaStorageService


def obtener_download_url(archivo_id: int) -> DownloadUrlOut:
    """
    Devuelve URL temporal GET si el archivo está READY y el usuario autorizado.

    Parámetros:
        archivo_id: PK de archivo.

    Retorno:
        DownloadUrlOut sin exponer object_key.

    Errores:
        ValueError: estado no descargable.
        MediaAccessError / RutaItemAccessError: autorización.
    """
    arch, _link = get_archivo_link_for_access(int(archivo_id))
    if arch.status != "READY":
        raise ValueError("El archivo no está disponible para descarga.")
    storage = MediaStorageService()
    presigned = storage.create_presigned_get(arch.object_key)
    return DownloadUrlOut(
        download_url=presigned.url,
        expires_at=presigned.expires_at,
    )
