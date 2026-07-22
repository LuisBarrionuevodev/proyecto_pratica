from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    ruta_item_reserva_orden_trabajo,
)
from app.models import IniciadorRuta, RutaItem, RutaTrabajo


def set_orden_trabajo_on_item(*, ruta_id: int, item_id: int, numero_orden_trabajo: str) -> RutaItem:
    """
    Asigna o reemplaza OT en un RutaItem activo de una ruta BORRADOR.

    Reglas:
    - Ruta debe existir y estar en BORRADOR.
    - Item debe existir, pertenecer a la ruta y no estar soft-deleted.
    - La OT se resuelve/crea por helper usando la fecha de la ruta.
    - No permite que una misma OT quede asociada a dos RutaItem activos distintos.

    Returns:
    - RutaItem actualizado.

    Raises:
    - LookupError: ruta/item no encontrados.
    - RuntimeError: estado inválido o conflicto OT ya usada por otro item activo.
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

    try:
        orden_trabajo = get_or_create_orden_trabajo(numero_orden_trabajo, ruta.fecha.isoformat())

        conflicts = (
            RutaItem.query.filter(
                RutaItem.id != item.id,
                RutaItem.deleted_at.is_(None),
                RutaItem.orden_trabajo_id == orden_trabajo.id,
            )
            .with_for_update()
            .all()
        )
        if any(ruta_item_reserva_orden_trabajo(conflict) for conflict in conflicts):
            raise RuntimeError("La orden de trabajo ya está asociada a otro item activo")

        item.orden_trabajo_id = orden_trabajo.id
        if item.estado_ruta_item != "ASIGNADO":
            item.estado_ruta_item = "ASIGNADO"
        db.session.add(item)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo asignar la orden de trabajo al item") from exc
    except Exception:
        db.session.rollback()
        raise

    refreshed = (
        RutaItem.query.filter(
            RutaItem.id == item_id,
            RutaItem.ruta_trabajo_id == ruta_id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.orden_trabajo),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.domicilio),
        )
        .first()
    )
    if not refreshed:
        raise LookupError("Item no encontrado para la ruta indicada")
    return refreshed
