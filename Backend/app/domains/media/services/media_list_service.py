"""Listado autorizado de archivos READY por RutaItem."""

from __future__ import annotations

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    assert_current_user_can_access_ruta_item,
)
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
    CATEGORIAS_MEDIA_HABILITADAS,
)
from app.domains.media.schemas.media_list_schemas import (
    ArchivoListItemOut,
    RutaItemArchivosListOut,
)
from app.models import Archivo, RutaItemArchivo


def listar_archivos_ruta_item(ruta_item_id: int) -> RutaItemArchivosListOut:
    """
    Devuelve archivos READY no eliminados agrupados por categoría de galería RutaItem.

    Parámetros:
        ruta_item_id: ítem ancla.

    Retorno:
        RutaItemArchivosListOut sin object_key ni URLs.

    Errores:
        RutaItemAccessError: scope inspector.
    """
    assert_current_user_can_access_ruta_item(int(ruta_item_id))
    rows = (
        db.session.query(RutaItemArchivo, Archivo)
        .join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            Archivo.status == "READY",
            Archivo.deleted_at.is_(None),
            RutaItemArchivo.categoria.in_(tuple(CATEGORIAS_MEDIA_HABILITADAS)),
        )
        .order_by(Archivo.uploaded_at.asc(), Archivo.id.asc())
        .all()
    )
    foto_acta: list[ArchivoListItemOut] = []
    foto_doc: list[ArchivoListItemOut] = []
    foto_inspeccion: list[ArchivoListItemOut] = []
    for link, arch in rows:
        if arch.uploaded_at is None:
            continue
        item = ArchivoListItemOut(
            archivo_id=int(arch.id),
            original_filename=arch.original_filename,
            content_type=arch.content_type,
            byte_size=int(arch.byte_size),
            uploaded_at=arch.uploaded_at,
            tipo_documento=link.tipo_documento,
            categoria=link.categoria,
        )
        if link.categoria == CATEGORIA_FOTO_ACTA:
            foto_acta.append(item)
        elif link.categoria == CATEGORIA_FOTO_DOCUMENTACION_LOCAL:
            foto_doc.append(item)
        elif link.categoria == CATEGORIA_FOTO_INSPECCION:
            foto_inspeccion.append(item)
    return RutaItemArchivosListOut(
        foto_acta=foto_acta,
        foto_documentacion_local=foto_doc,
        foto_inspeccion=foto_inspeccion,
    )
