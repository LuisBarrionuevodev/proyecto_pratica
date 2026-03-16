from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.models import RutaItem, RutaTrabajo


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

        conflict = (
            RutaItem.query.filter(
                RutaItem.id != item.id,
                RutaItem.deleted_at.is_(None),
                RutaItem.orden_trabajo_id == orden_trabajo.id,
            )
            .with_for_update()
            .first()
        )
        if conflict:
            raise RuntimeError("La orden de trabajo ya está asociada a otro item activo")

        item.orden_trabajo_id = orden_trabajo.id
        db.session.add(item)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo asignar la orden de trabajo al item") from exc
    except Exception:
        db.session.rollback()
        raise

    return item
