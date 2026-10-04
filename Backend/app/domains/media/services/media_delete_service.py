"""Eliminación autorizada de archivos Media.1A."""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.domains.media.constants import CATEGORIAS_MEDIA_HABILITADAS
from app.domains.media.schemas.media_list_schemas import ArchivoDeleteOut
from app.domains.media.services.media_access_service import (
    MediaAccessError,
    get_archivo_link_for_access,
)
from app.domains.media.services.media_storage_service import MediaStorageService
from app.domains.media.utils.media_observability import log_archivo_delete_ok, log_storage_error

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
    if link.categoria not in CATEGORIAS_MEDIA_HABILITADAS:
        raise ValueError("Categoría no eliminable.")
    if arch.status == "DELETED" or arch.deleted_at is not None:
        raise MediaAccessError("Archivo no encontrado.", status_code=404)
    if arch.status != "READY":
        raise ValueError("Solo se pueden eliminar archivos en estado READY.")

    storage = MediaStorageService()
    try:
        storage.delete_object(arch.object_key)
    except Exception as exc:
        log_storage_error(
            operation="delete_object",
            cause=type(exc).__name__,
            archivo_id=int(arch.id),
        )
        raise ValueError("No se pudo eliminar el archivo del storage.") from exc

    now = datetime.utcnow()
    arch.status = "DELETED"
    arch.deleted_at = now
    arch.deleted_by_user_id = int(actor_user_id)
    db.session.commit()

    log_archivo_delete_ok(
        archivo_id=int(arch.id),
        ruta_item_id=int(link.ruta_item_id),
        categoria=link.categoria,
    )

    return ArchivoDeleteOut(archivo_id=int(arch.id), status="DELETED")
