"""Eliminación autorizada de archivos Media.1A."""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
)
from app.domains.media.schemas.media_list_schemas import ArchivoDeleteOut
from app.domains.media.services.media_access_service import (
    MediaAccessError,
    get_archivo_link_for_access,
)
from app.domains.media.services.media_storage_service import MediaStorageService

_CATEGORIAS_ELIMINABLES_1A = frozenset(
    {
        CATEGORIA_FOTO_ACTA,
        CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    }
)


def eliminar_archivo(archivo_id: int, actor_user_id: int) -> ArchivoDeleteOut:
    """
    Borra objeto del bucket y marca metadata DELETED (libera cupo).

    Parámetros:
        archivo_id: PK de archivo.
        actor_user_id: usuario autenticado.

    Retorno:
        ArchivoDeleteOut.

    Errores:
        ValueError: categoría no eliminable o estado inválido.
        MediaAccessError / RutaItemAccessError: autorización.
    """
    arch, link = get_archivo_link_for_access(int(archivo_id))
    if link.categoria == CATEGORIA_FOTO_INSPECCION:
        raise ValueError("La categoría FOTO_INSPECCION no está habilitada.")
    if link.categoria not in _CATEGORIAS_ELIMINABLES_1A:
        raise ValueError("Categoría no eliminable.")
    if arch.status == "DELETED" or arch.deleted_at is not None:
        raise MediaAccessError("Archivo no encontrado.", status_code=404)
    if arch.status != "READY":
        raise ValueError("Solo se pueden eliminar archivos en estado READY.")

    storage = MediaStorageService()
    try:
        storage.delete_object(arch.object_key)
    except Exception as exc:
        raise ValueError("No se pudo eliminar el archivo del storage.") from exc

    now = datetime.utcnow()
    arch.status = "DELETED"
    arch.deleted_at = now
    arch.deleted_by_user_id = int(actor_user_id)
    db.session.commit()

    return ArchivoDeleteOut(archivo_id=int(arch.id), status="DELETED")
