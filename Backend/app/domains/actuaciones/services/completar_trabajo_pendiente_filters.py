"""Filtros compartidos para ítems pendientes en Completar trabajo (MEDIA.2D)."""

from __future__ import annotations

from sqlalchemy import and_, exists, or_

from app.models import Archivo, RutaItem, RutaItemArchivo


def pending_archivo_exists_correlated():
    """EXISTS de archivos PENDING activos en el mismo RutaItem."""
    return exists().where(
        and_(
            RutaItemArchivo.ruta_item_id == RutaItem.id,
            RutaItemArchivo.archivo_id == Archivo.id,
            Archivo.status == "PENDING",
            Archivo.deleted_at.is_(None),
        )
    )


def ruta_item_pendiente_completar_trabajo_clause():
    """
    Ítem visible en Completar trabajo: cierre alfanumérico pendiente o fotos pendientes tras cierre.
    Excluye ítems con ``fotos_pendientes_cerradas_at`` (finalizar por ahora).
    """
    pending_media = pending_archivo_exists_correlated()
    fotos_pendientes_tras_cierre = and_(
        RutaItem.estado_ruta_item == "FINALIZADO",
        RutaItem.fotos_pendientes_cerradas_at.is_(None),
        or_(
            pending_media,
            RutaItem.evidencias_pendientes_abiertas.is_(True),
        ),
    )
    return and_(
        RutaItem.fotos_pendientes_cerradas_at.is_(None),
        or_(
            RutaItem.estado_ruta_item == "EN_PROCESO",
            fotos_pendientes_tras_cierre,
        ),
    )
