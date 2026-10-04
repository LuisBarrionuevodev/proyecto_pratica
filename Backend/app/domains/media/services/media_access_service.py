"""Autorización de archivos vía RutaItem (mismo scope que Completar Trabajo)."""

from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    RutaItemAccessError,
    assert_current_user_can_access_ruta_item,
)
from app.models import Archivo, RutaItemArchivo


class MediaAccessError(Exception):
    """Error de acceso a media (404/403)."""

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_archivo_link_for_access(archivo_id: int) -> tuple[Archivo, RutaItemArchivo]:
    """
    Carga archivo y vínculo autorizando al usuario actual sobre el RutaItem.

    Parámetros:
        archivo_id: PK de ``archivo``.

    Retorno:
        Tupla (archivo, ruta_item_archivo).

    Errores:
        MediaAccessError: 404 inexistente o borrado lógico.
        RutaItemAccessError: 401/403 scope.
    """
    link = (
        RutaItemArchivo.query.filter(RutaItemArchivo.archivo_id == int(archivo_id))
        .order_by(RutaItemArchivo.id.desc())
        .first()
    )
    if link is None:
        raise MediaAccessError("Archivo no encontrado.", status_code=404)
    arch = Archivo.query.get(int(archivo_id))
    if arch is None or arch.deleted_at is not None:
        raise MediaAccessError("Archivo no encontrado.", status_code=404)
    assert_current_user_can_access_ruta_item(int(link.ruta_item_id))
    return arch, link
