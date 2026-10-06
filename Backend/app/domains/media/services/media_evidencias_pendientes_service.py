"""Actualiza flag evidencias_pendientes_abiertas en RutaItem tras uploads."""

from __future__ import annotations

from app.database import db
from app.domains.media.services.media_ruta_item_resumen_service import ruta_item_tiene_archivos_pending
from app.models import RutaItem, RutaItemArchivo


def maybe_clear_evidencias_pendientes_abiertas(archivo_id: int) -> None:
    """
    Si no quedan archivos PENDING en el ítem, limpia evidencias_pendientes_abiertas.

    Parámetros:
        archivo_id: archivo recién completado o actualizado.

    No hace commit.
    """
    link = (
        RutaItemArchivo.query.filter_by(archivo_id=int(archivo_id))
        .order_by(RutaItemArchivo.id.asc())
        .first()
    )
    if not link:
        return
    ruta_item_id = int(link.ruta_item_id)
    if ruta_item_tiene_archivos_pending(ruta_item_id):
        return
    item = db.session.get(RutaItem, ruta_item_id)
    if item and item.evidencias_pendientes_abiertas:
        item.evidencias_pendientes_abiertas = False
        db.session.add(item)
