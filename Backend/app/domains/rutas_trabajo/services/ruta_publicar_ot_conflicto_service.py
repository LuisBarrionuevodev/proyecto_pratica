from __future__ import annotations

from dataclasses import dataclass

from app.models import Actuaciones, IniciadorRuta, RutaItem, RutaTrabajo


@dataclass(frozen=True)
class ConflictoOrdenTrabajoPublicar:
    """Detalle de una actuación que bloquea el uso de una OT al publicar."""

    actuacion_id: int
    orden_trabajo_id: int
    ruta_item_id: int | None
    ruta_trabajo_id: int | None
    estado_ruta: str | None
    estado_ruta_item: str | None
    estado_ejecucion: str | None
    item_deleted_at: bool


def _ruta_item_libera_reserva_ot(item: RutaItem) -> bool:
    """
    Indica si un ítem de ruta ya no reserva su OT para nuevas publicaciones.

    Parámetros:
        item: `RutaItem` vinculado a la actuación en conflicto.

    Retorno:
        True si el ítem no debería bloquear reutilización de la OT.
    """
    if item.deleted_at is not None:
        return True
    if item.estado_ruta_item == "CANCELADO":
        return True
    if item.estado_ruta_item == "NO_REALIZADO":
        return True
    if item.estado_ruta_item == "FINALIZADO" and item.estado_ejecucion == "NO_REALIZADO":
        return True
    return False


def ruta_item_reserva_orden_trabajo(item: RutaItem) -> bool:
    """
    Indica si un ítem activo reserva su OT (p. ej. al asignar OT en borrador).

    Parámetros:
        item: ítem candidato a conflicto.

    Retorno:
        True si el ítem impide reutilizar la misma OT en otro ítem.
    """
    return not _ruta_item_libera_reserva_ot(item)


def actuacion_reserva_orden_trabajo(
    actuacion: Actuaciones,
    *,
    excluir_ruta_item_id: int | None = None,
) -> bool:
    """
    Determina si una actuación mantiene reservada su orden de trabajo.

    Parámetros:
        actuacion: actuación candidata a conflicto.
        excluir_ruta_item_id: ítem actual en publicación (no aplica reserva propia).

    Retorno:
        True si la OT sigue en uso operativo real.
    """
    items = (
        RutaItem.query.filter(RutaItem.actuacion_id == actuacion.id)
        .order_by(RutaItem.id.desc())
        .all()
    )
    if not items:
        return True

    for item in items:
        if excluir_ruta_item_id is not None and item.id == excluir_ruta_item_id:
            continue
        if not _ruta_item_libera_reserva_ot(item):
            return True
    return False


def buscar_conflicto_orden_trabajo_al_publicar(
    *,
    orden_trabajo_id: int,
    ruta_item_id: int,
    iniciador_ruta_id: int,
) -> ConflictoOrdenTrabajoPublicar | None:
    """
    Busca una actuación activa que impida publicar con la OT indicada.

    Ignora actuaciones ligadas solo a ítems anulados, soft-deleted o no realizados
    reencolables.

    Parámetros:
        orden_trabajo_id: OT del ítem a publicar.
        ruta_item_id: ítem en publicación.
        iniciador_ruta_id: iniciador del ítem (trazabilidad).

    Retorno:
        Detalle del bloqueo o None si la OT está disponible.
    """
    _ = iniciador_ruta_id
    candidatas = (
        Actuaciones.query.filter(Actuaciones.orden_trabajo_id == orden_trabajo_id)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    for act in candidatas:
        if not actuacion_reserva_orden_trabajo(act, excluir_ruta_item_id=ruta_item_id):
            continue

        item_bloqueo = (
            RutaItem.query.filter(
                RutaItem.actuacion_id == act.id,
                RutaItem.id != ruta_item_id,
            )
            .order_by(RutaItem.id.desc())
            .first()
        )
        ruta_estado: str | None = None
        if item_bloqueo is not None:
            ruta = RutaTrabajo.query.get(item_bloqueo.ruta_trabajo_id)
            ruta_estado = ruta.estado_ruta if ruta else None

        return ConflictoOrdenTrabajoPublicar(
            actuacion_id=act.id,
            orden_trabajo_id=orden_trabajo_id,
            ruta_item_id=item_bloqueo.id if item_bloqueo else None,
            ruta_trabajo_id=item_bloqueo.ruta_trabajo_id if item_bloqueo else None,
            estado_ruta=ruta_estado,
            estado_ruta_item=item_bloqueo.estado_ruta_item if item_bloqueo else None,
            estado_ejecucion=item_bloqueo.estado_ejecucion if item_bloqueo else None,
            item_deleted_at=bool(item_bloqueo and item_bloqueo.deleted_at is not None),
        )
    return None


def buscar_actuacion_reintento_reutilizable(
    iniciador_ruta_id: int,
) -> Actuaciones | None:
    """
    Actuación de un intento anterior no realizado del mismo iniciador, reutilizable al republicar.

    Parámetros:
        iniciador_ruta_id: iniciador en planificación.

    Retorno:
        Actuación previa si proviene de un cierre NO_REALIZADO reencolable; si no, None.
    """
    item_previo = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == iniciador_ruta_id,
            RutaItem.actuacion_id.isnot(None),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if not item_previo or not item_previo.actuacion_id:
        return None
    return Actuaciones.query.get(item_previo.actuacion_id)


def validar_orden_trabajo_disponible_para_publicar(
    *,
    orden_trabajo_id: int,
    ruta_item_id: int,
    iniciador: IniciadorRuta,
) -> None:
    """
    Valida que la OT no esté reservada por otra actuación operativa.

    Parámetros:
        orden_trabajo_id: OT del ítem.
        ruta_item_id: ítem en publicación.
        iniciador: iniciador del ítem.

    Errores:
        RuntimeError: conflicto real de OT con detalle del registro bloqueante.
    """
    conflicto = buscar_conflicto_orden_trabajo_al_publicar(
        orden_trabajo_id=orden_trabajo_id,
        ruta_item_id=ruta_item_id,
        iniciador_ruta_id=iniciador.id,
    )
    if not conflicto:
        return

    partes = [
        f"La orden de trabajo ya está asociada a la actuación {conflicto.actuacion_id}",
    ]
    if conflicto.ruta_item_id is not None:
        partes.append(f" (ítem de ruta {conflicto.ruta_item_id}")
        if conflicto.ruta_trabajo_id is not None:
            partes.append(f", ruta {conflicto.ruta_trabajo_id}")
        if conflicto.estado_ruta:
            partes.append(f", estado ruta {conflicto.estado_ruta}")
        if conflicto.estado_ruta_item:
            partes.append(f", ítem {conflicto.estado_ruta_item}")
        if conflicto.estado_ejecucion:
            partes.append(f"/{conflicto.estado_ejecucion}")
        partes.append(")")
    partes.append(f"; no se puede publicar el ítem {ruta_item_id}.")
    raise RuntimeError("".join(partes))
