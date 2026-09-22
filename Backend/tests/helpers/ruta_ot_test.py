"""Helpers de test para OT en rutas (OT-AUTO: bypass de endpoints manuales deprecados)."""

from __future__ import annotations

from app.database import db
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.models import RutaItem, RutaTrabajo


def asignar_ot_legacy_en_item(
    *,
    ruta_id: int,
    item_id: int,
    numero_orden_trabajo: str,
) -> RutaItem:
    """
    Simula borrador legacy con OT preasignada (solo tests de transición).

    No usa el endpoint/service OT-AUTO deprecado; escribe directamente en DB.

    Parámetros:
        ruta_id: ruta BORRADOR.
        item_id: ítem activo.
        numero_orden_trabajo: número OT manual histórico.

    Retorno:
        ``RutaItem`` actualizado.

    Errores:
        LookupError: ruta o ítem inexistente.
        RuntimeError: ruta no BORRADOR.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("La ruta debe estar en BORRADOR")

    item = RutaItem.query.filter(
        RutaItem.id == item_id,
        RutaItem.ruta_trabajo_id == ruta_id,
        RutaItem.deleted_at.is_(None),
    ).first()
    if not item:
        raise LookupError("Item no encontrado para la ruta indicada")

    ot = get_or_create_orden_trabajo(numero_orden_trabajo, ruta.fecha.isoformat())
    item.orden_trabajo_id = ot.id
    if item.estado_ruta_item != "ASIGNADO":
        item.estado_ruta_item = "ASIGNADO"
    db.session.add(item)
    db.session.commit()
    return item
