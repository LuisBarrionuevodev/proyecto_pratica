from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    ruta_item_reserva_orden_trabajo,
    validar_orden_trabajo_disponible_para_publicar,
)
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
    log_publicar_debug,
    parse_integrity_error,
    raise_publicar_debug,
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
    - Una OT consumida por actuación de otro iniciador (incluso NO_REALIZADA) bloquea
      inmediatamente (regla PR11.1f / PR11.1g).

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

    item = (
        RutaItem.query.filter(
            RutaItem.id == item_id,
            RutaItem.ruta_trabajo_id == ruta_id,
            RutaItem.deleted_at.is_(None),
        )
        .options(joinedload(RutaItem.iniciador_ruta))
        .first()
    )
    if not item:
        raise LookupError("Item no encontrado para la ruta indicada")

    try:
        orden_trabajo = get_or_create_orden_trabajo(numero_orden_trabajo, ruta.fecha.isoformat())

        validar_orden_trabajo_disponible_para_publicar(
            orden_trabajo_id=int(orden_trabajo.id),
            ruta_item_id=item.id,
            iniciador=item.iniciador_ruta,
            ruta=ruta,
            item=item,
        )

        conflicts = (
            RutaItem.query.filter(
                RutaItem.id != item.id,
                RutaItem.deleted_at.is_(None),
                RutaItem.orden_trabajo_id == orden_trabajo.id,
            )
            .with_for_update()
            .all()
        )
        blocking = [c for c in conflicts if ruta_item_reserva_orden_trabajo(c)]
        if blocking:
            conflict = blocking[0]
            ini = IniciadorRuta.query.get(conflict.iniciador_ruta_id)
            debug = log_publicar_debug(
                conflicto_detectado_por="set_orden_trabajo_on_item.conflicto_item",
                mensaje_conflicto="La orden de trabajo ya está asociada a otro item activo",
                ruta_id=ruta_id,
                ruta_fecha=ruta.fecha.isoformat(),
                item_id=item_id,
                iniciador_id=item.iniciador_ruta_id,
                orden_trabajo_id=orden_trabajo.id,
                numero_orden_trabajo=orden_trabajo.numero_acta,
                item_bloqueante_id=conflict.id,
                item_bloqueante_ruta_id=conflict.ruta_trabajo_id,
                item_bloqueante_estado=conflict.estado_ruta_item,
                item_bloqueante_estado_ejecucion=conflict.estado_ejecucion,
                item_bloqueante_iniciador_id=conflict.iniciador_ruta_id,
                item_bloqueante_iniciador_estado=ini.estado_iniciador if ini else None,
            )
            raise_publicar_debug(
                "La orden de trabajo ya está asociada a otro item activo",
                validator="set_orden_trabajo_on_item",
                debug=debug,
            )

        item.orden_trabajo_id = orden_trabajo.id
        if item.estado_ruta_item != "ASIGNADO":
            item.estado_ruta_item = "ASIGNADO"
        db.session.add(item)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        debug = parse_integrity_error(exc)
        debug.update(
            {
                "ruta_id": ruta_id,
                "item_id": item_id,
                "numero_orden_trabajo": numero_orden_trabajo,
                "fase": "set_orden_trabajo_on_item",
            }
        )
        raise_publicar_debug(
            f"No se pudo asignar la orden de trabajo al item: {debug.get('message', exc)}",
            validator="IntegrityError_set_orden_trabajo_on_item",
            debug=debug,
            cause=exc,
        )
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
