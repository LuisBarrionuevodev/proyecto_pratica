"""Filtros compartidos para ítems pendientes en Completar trabajo (MEDIA.2D / 2D.1)."""

from __future__ import annotations

from sqlalchemy import and_, exists, or_

from app.domains.media.constants import UPLOAD_ORIGIN_COMPLETAR_TRABAJO, UPLOAD_ORIGIN_MIS_TRABAJOS
from app.models import Archivo, RutaItem, RutaItemArchivo


def pending_archivo_exists_correlated():
    """EXISTS de archivos PENDING activos en el mismo RutaItem (cualquier origen)."""
    return exists().where(
        and_(
            RutaItemArchivo.ruta_item_id == RutaItem.id,
            RutaItemArchivo.archivo_id == Archivo.id,
            Archivo.status == "PENDING",
            Archivo.deleted_at.is_(None),
        )
    )


def pending_archivo_completar_trabajo_exists_correlated():
    """EXISTS de archivos PENDING de evidencia obligatoria (Completar trabajo)."""
    return exists().where(
        and_(
            RutaItemArchivo.ruta_item_id == RutaItem.id,
            RutaItemArchivo.archivo_id == Archivo.id,
            Archivo.status == "PENDING",
            Archivo.deleted_at.is_(None),
            or_(
                RutaItemArchivo.upload_origin == UPLOAD_ORIGIN_COMPLETAR_TRABAJO,
                RutaItemArchivo.upload_origin.is_(None),
            ),
        )
    )


def fotos_pendientes_obligatorias_tras_cierre_clause():
    """
    Ítem FINALIZADO con evidencia obligatoria de cierre pendiente (MEDIA.2D.1).

    Un archivo PENDING de Mis trabajos no activa este criterio.
    """
    return and_(
        RutaItem.estado_ruta_item == "FINALIZADO",
        RutaItem.fotos_pendientes_cerradas_at.is_(None),
        RutaItem.evidencias_pendientes_abiertas.is_(True),
    )


def ruta_item_pendiente_completar_trabajo_clause():
    """
    Ítem visible en Completar trabajo: cierre alfanumérico pendiente o evidencia obligatoria tras cierre.
    Excluye ítems con ``fotos_pendientes_cerradas_at`` (finalizar por ahora).
    """
    return and_(
        RutaItem.fotos_pendientes_cerradas_at.is_(None),
        or_(
            RutaItem.estado_ruta_item == "EN_PROCESO",
            fotos_pendientes_obligatorias_tras_cierre_clause(),
        ),
    )


def _pending_completar_trabajo_filter(ruta_item_id: int):
    return and_(
        RutaItemArchivo.ruta_item_id == int(ruta_item_id),
        Archivo.status == "PENDING",
        Archivo.deleted_at.is_(None),
        or_(
            RutaItemArchivo.upload_origin == UPLOAD_ORIGIN_COMPLETAR_TRABAJO,
            RutaItemArchivo.upload_origin.is_(None),
        ),
    )


def count_pending_completar_trabajo(ruta_item_id: int) -> int:
    """Cantidad de archivos PENDING de evidencia obligatoria en el ítem."""
    return int(
        RutaItemArchivo.query.join(Archivo, Archivo.id == RutaItemArchivo.archivo_id)
        .filter(_pending_completar_trabajo_filter(ruta_item_id))
        .count()
    )


def ruta_item_tiene_pending_completar_trabajo(ruta_item_id: int) -> bool:
    """True si quedan archivos PENDING de origen Completar trabajo en el ítem."""
    return count_pending_completar_trabajo(ruta_item_id) > 0


def normalize_upload_origin_for_create(origin: str | None) -> str:
    """Valida origen de carga; default Completar trabajo."""
    if origin is None or origin == UPLOAD_ORIGIN_COMPLETAR_TRABAJO:
        return UPLOAD_ORIGIN_COMPLETAR_TRABAJO
    if origin == UPLOAD_ORIGIN_MIS_TRABAJOS:
        return UPLOAD_ORIGIN_MIS_TRABAJOS
    raise ValueError("upload_origin inválido.")
