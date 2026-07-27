from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from sqlalchemy import and_, or_

from app.database import db
from app.models import Actuaciones, IniciadorRuta, OrdenTrabajo, RutaItem, RutaTrabajo

from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
    conflicto_ot_a_debug,
    log_publicar_debug,
    raise_publicar_debug,
)


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


def _item_es_reintento_no_realizado(
    item: RutaItem,
    *,
    incluir_soft_deleted: bool = False,
) -> bool:
    """
    True si el ítem cerró un intento reencolable (contraproducencia / no realizado).

    Acepta el par canónico FINALIZADO+NO_REALIZADO, el legado ``estado_ruta_item=NO_REALIZADO``
    y ``estado_ejecucion=NO_REALIZADO`` aunque el estado de ítem no esté alineado.
    """
    if item.deleted_at is not None and not incluir_soft_deleted:
        return False
    if item.estado_ruta_item == "NO_REALIZADO":
        return True
    if item.estado_ejecucion == "NO_REALIZADO":
        return True
    return item.estado_ruta_item == "FINALIZADO" and item.estado_ejecucion == "NO_REALIZADO"


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
        # Actuación documental sin ítem de ruta (p. ej. inspección base de reinspección).
        # Un intento NO_REALIZADO con contraproducencia no reserva la OT.
        if actuacion.contraproducencia:
            return False
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
    act_reintento = buscar_actuacion_reintento_reutilizable(iniciador_ruta_id)
    candidatas = (
        Actuaciones.query.filter(Actuaciones.orden_trabajo_id == orden_trabajo_id)
        .order_by(Actuaciones.id.desc())
        .all()
    )
    for act in candidatas:
        if act_reintento is not None and int(act.id) == int(act_reintento.id):
            continue
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


def _buscar_actuacion_desde_items_no_realizado(
    iniciador_ruta_id: int,
) -> Actuaciones | None:
    """
    Busca actuación reutilizable a partir de ítems NO_REALIZADO del iniciador.

    Prefiere ítems activos (no soft-deleted) y el más reciente por id.
    """
    filtro_estado = or_(
        and_(
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "NO_REALIZADO",
        ),
        RutaItem.estado_ruta_item == "NO_REALIZADO",
        RutaItem.estado_ejecucion == "NO_REALIZADO",
    )
    candidatos = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == iniciador_ruta_id,
            RutaItem.actuacion_id.isnot(None),
            filtro_estado,
        )
        .order_by(RutaItem.id.desc())
        .all()
    )
    for item in candidatos:
        if not _item_es_reintento_no_realizado(item, incluir_soft_deleted=True):
            continue
        if item.deleted_at is not None:
            continue
        act = Actuaciones.query.get(item.actuacion_id)
        if act is not None:
            return act
    for item in candidatos:
        if not _item_es_reintento_no_realizado(item, incluir_soft_deleted=True):
            continue
        act = Actuaciones.query.get(item.actuacion_id)
        if act is not None:
            return act
    return None


def _buscar_actuacion_por_contraproducencia_liberada(
    iniciador_ruta_id: int,
) -> Actuaciones | None:
    """
    Fallback: actuación con contraproducencia cuyos ítems ya no reservan la OT.

    Cubre datos legados donde el ítem no tiene el par canónico de estados pero el
    cierre operativo dejó ``contraproducencia`` en la actuación.
    """
    act_ids = (
        db.session.query(RutaItem.actuacion_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_ruta_id,
            RutaItem.actuacion_id.isnot(None),
        )
        .distinct()
        .all()
    )
    for (act_id,) in sorted((row[0] for row in act_ids), reverse=True):
        act = Actuaciones.query.get(act_id)
        if act is None or not (act.contraproducencia or "").strip():
            continue
        if not actuacion_reserva_orden_trabajo(act):
            return act
    return None


def actuacion_pertenece_iniciador(
    actuacion_id: int,
    iniciador_ruta_id: int,
) -> bool:
    """
    True si la actuación pertenece al iniciador (ítem de ruta o actuación origen).

    Parámetros:
        actuacion_id: PK de ``actuaciones``.
        iniciador_ruta_id: PK de ``iniciador_ruta``.

    Retorno:
        True si existe vínculo operativo o documental (``iniciador_ruta.actuacion_id``).
    """
    ini = db.session.get(IniciadorRuta, iniciador_ruta_id)
    if ini is not None and ini.actuacion_id is not None and int(ini.actuacion_id) == int(actuacion_id):
        return True
    return (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == iniciador_ruta_id,
            RutaItem.actuacion_id == actuacion_id,
        ).first()
        is not None
    )


def buscar_actuacion_ocupante_orden_trabajo(
    orden_trabajo_id: int,
    *,
    excluir_actuacion_id: int | None = None,
) -> Actuaciones | None:
    """
    Actuación que ya posee la OT indicada (índice único ``orden_trabajo_id``).

    Parámetros:
        orden_trabajo_id: OT objetivo.
        excluir_actuacion_id: actuación en reutilización (no contar como ocupante).

    Retorno:
        Fila existente con esa OT o None.
    """
    q = Actuaciones.query.filter(Actuaciones.orden_trabajo_id == orden_trabajo_id)
    if excluir_actuacion_id is not None:
        q = q.filter(Actuaciones.id != excluir_actuacion_id)
    return q.first()


def _item_ocupante_de_actuacion(actuacion_id: int) -> RutaItem | None:
    """Ítem de ruta más reciente vinculado a una actuación (si existe)."""
    return (
        RutaItem.query.filter(RutaItem.actuacion_id == actuacion_id)
        .order_by(RutaItem.id.desc())
        .first()
    )


def buscar_ocupante_ot_de_otro_iniciador(
    *,
    orden_trabajo_id: int,
    iniciador_ruta_id: int,
) -> Actuaciones | None:
    """
    Actuación que consume la OT si pertenece a otro iniciador/flujo.

    Regla operativa (PR11.1f / PR11.1g): una OT queda consumida al ser usada en una
    actuación, incluso si la actuación finaliza como NO_REALIZADA. Los reintentos deben
    usar una OT libre, salvo reutilización interna de la misma actuación del mismo
    iniciador cuando corresponda.

    Parámetros:
        orden_trabajo_id: OT del ítem en publicación.
        iniciador_ruta_id: iniciador que intenta publicar.

    Retorno:
        Actuación ocupante de otro flujo, o None si no hay bloqueo por consumo externo.
    """
    ocupante = buscar_actuacion_ocupante_orden_trabajo(orden_trabajo_id)
    if ocupante is None:
        return None
    if actuacion_pertenece_iniciador(ocupante.id, iniciador_ruta_id):
        return None
    return ocupante


def raise_orden_trabajo_ocupada_por_otro_flujo(
    *,
    orden_trabajo_id: int,
    ruta_item_id: int,
    ocupante: Actuaciones,
    iniciador: IniciadorRuta | None = None,
    item: RutaItem | None = None,
    ruta: RutaTrabajo | None = None,
    extra_debug: dict[str, Any] | None = None,
) -> None:
    """
    Lanza 409 cuando la OT ya fue consumida por una actuación de otro flujo.

    Parámetros:
        orden_trabajo_id: OT bloqueada.
        ruta_item_id: ítem en publicación.
        ocupante: actuación que ya posee la OT.
        iniciador: iniciador del ítem en publicación (contexto debug).
        item: ítem en publicación (contexto debug).
        ruta: ruta en publicación (contexto debug).
        extra_debug: campos adicionales para QA.

    Errores:
        RutaPublicarDebugError: siempre, con validator ``orden_trabajo_ocupada_por_otro_flujo``.
    """
    ot = db.session.get(OrdenTrabajo, orden_trabajo_id)
    numero_ot = ot.numero_acta if ot else str(orden_trabajo_id)
    item_ocupante = _item_ocupante_de_actuacion(ocupante.id)

    mensaje = (
        f"La orden de trabajo {numero_ot} ya fue utilizada en otra actuación. "
        "Aunque el trabajo haya sido no realizado, esa OT queda consumida. "
        "Seleccione una orden de trabajo libre."
    )

    debug: dict[str, Any] = {
        "validator": "orden_trabajo_ocupada_por_otro_flujo",
        "orden_trabajo_id": orden_trabajo_id,
        "numero_orden_trabajo": numero_ot,
        "ruta_item_id": ruta_item_id,
        "actuacion_ocupante_id": ocupante.id,
        "actuacion_ocupante_tipo": ocupante.tipo,
        "actuacion_ocupante_contraproducencia": ocupante.contraproducencia,
        "iniciador_ocupante_id": (
            item_ocupante.iniciador_ruta_id if item_ocupante is not None else None
        ),
        "estado_ejecucion_ocupante": (
            item_ocupante.estado_ejecucion if item_ocupante is not None else None
        ),
        "estado_item_ocupante": (
            item_ocupante.estado_ruta_item if item_ocupante is not None else None
        ),
    }
    if item_ocupante is not None:
        debug["actuacion_ocupante_item_id"] = item_ocupante.id
    if item is not None and iniciador is not None:
        from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
            snapshot_item_publicar_context,
        )

        numero_ot_debug = debug.get("numero_orden_trabajo")
        orden_trabajo_id_debug = debug.get("orden_trabajo_id")
        debug.update(
            snapshot_item_publicar_context(
                ruta=ruta,
                item=item,
                iniciador=iniciador,
            )
        )
        if numero_ot_debug is not None:
            debug["numero_orden_trabajo"] = numero_ot_debug
        if orden_trabajo_id_debug is not None:
            debug["orden_trabajo_id"] = orden_trabajo_id_debug
    if extra_debug:
        debug.update(extra_debug)

    raise_publicar_debug(
        mensaje,
        validator="orden_trabajo_ocupada_por_otro_flujo",
        debug=debug,
    )


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
    act = _buscar_actuacion_desde_items_no_realizado(iniciador_ruta_id)
    if act is not None:
        return act
    return _buscar_actuacion_por_contraproducencia_liberada(iniciador_ruta_id)


def resolver_actuacion_para_publicar_item(
    *,
    iniciador_ruta_id: int,
    orden_trabajo_id: int,
) -> Actuaciones | None:
    """
    Resuelve qué actuación reutilizar al publicar, evitando INSERT duplicado por ``orden_trabajo_id``.

    Regla operativa: una OT queda consumida al usarse en una actuación, incluso si finaliza
    como NO_REALIZADA. Los reintentos deben usar una OT libre, salvo reutilización interna de
    la misma actuación del mismo iniciador cuando corresponda.

    Prioridad:
    1. Actuación del iniciador que ya tiene la OT objetivo (reintento misma OT).
    2. Actuación reencolable genérica (``buscar_actuacion_reintento_reutilizable``).
    3. Si la OT objetivo está ocupada por otra actuación del mismo iniciador reencolable,
       reutilizar esa fila en lugar de actualizar la OT de la actuación previa.

    Parámetros:
        iniciador_ruta_id: iniciador del ítem en publicación.
        orden_trabajo_id: OT del ítem a publicar.

    Retorno:
        Actuación a reutilizar o None si debe crearse una nueva.
    """
    act_con_ot_objetivo = (
        db.session.query(Actuaciones)
        .join(RutaItem, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_ruta_id,
            Actuaciones.orden_trabajo_id == orden_trabajo_id,
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if act_con_ot_objetivo is not None:
        return act_con_ot_objetivo

    reintento = buscar_actuacion_reintento_reutilizable(iniciador_ruta_id)
    if reintento is None:
        return None

    if int(reintento.orden_trabajo_id or 0) == int(orden_trabajo_id):
        return reintento

    ocupante = buscar_actuacion_ocupante_orden_trabajo(
        orden_trabajo_id,
        excluir_actuacion_id=reintento.id,
    )
    if ocupante is None:
        return reintento

    # PR11.1f: si la OT objetivo ya está en otra actuación del mismo iniciador, reutilizar
    # esa fila en lugar de actualizar ``reintento`` (evita IntegrityError ix_orden_trabajo_id).
    if actuacion_pertenece_iniciador(ocupante.id, iniciador_ruta_id):
        return ocupante

    # OT tomada por otro flujo: no devolver ``reintento`` (el UPDATE fallaría en commit).
    return None


def evaluar_actuacion_para_publicar_item(
    *,
    iniciador_ruta_id: int,
    orden_trabajo_id: int,
    ruta_item_id: int,
    iniciador: IniciadorRuta | None = None,
    item: RutaItem | None = None,
    ruta: RutaTrabajo | None = None,
) -> Actuaciones | None:
    """
    Resuelve actuación reutilizable o indica creación nueva; bloqueos reales → 409 explícito.

    Parámetros:
        iniciador_ruta_id: iniciador del ítem.
        orden_trabajo_id: OT del ítem en publicación.
        ruta_item_id: ítem en publicación (contexto debug).
        iniciador: iniciador cargado (opcional).
        item: ítem cargado (opcional).
        ruta: ruta en publicación (opcional).

    Retorno:
        Actuación a reutilizar o None si debe crearse una nueva.

    Errores:
        RutaPublicarDebugError: OT ocupada por actuación de otro flujo/iniciador.
    """
    act = resolver_actuacion_para_publicar_item(
        iniciador_ruta_id=iniciador_ruta_id,
        orden_trabajo_id=orden_trabajo_id,
    )
    if act is not None:
        return act

    ocupante = buscar_actuacion_ocupante_orden_trabajo(orden_trabajo_id)
    if ocupante is None:
        return None

    if actuacion_pertenece_iniciador(ocupante.id, iniciador_ruta_id):
        return ocupante

    ini = iniciador or db.session.get(IniciadorRuta, iniciador_ruta_id)
    item_ctx = item or db.session.get(RutaItem, ruta_item_id)
    raise_orden_trabajo_ocupada_por_otro_flujo(
        orden_trabajo_id=orden_trabajo_id,
        ruta_item_id=ruta_item_id,
        ocupante=ocupante,
        iniciador=ini,
        item=item_ctx,
        ruta=ruta,
    )


def validar_orden_trabajo_disponible_para_publicar(
    *,
    orden_trabajo_id: int,
    ruta_item_id: int,
    iniciador: IniciadorRuta,
    ruta: RutaTrabajo | None = None,
    item: RutaItem | None = None,
) -> None:
    """
    Valida que la OT no esté reservada por otra actuación operativa.

    Parámetros:
        orden_trabajo_id: OT del ítem.
        ruta_item_id: ítem en publicación.
        iniciador: iniciador del ítem.
        ruta: ruta en publicación (contexto debug).
        item: ítem en publicación (contexto debug).

    Errores:
        RutaPublicarDebugError: conflicto real de OT con detalle del registro bloqueante.
    """
    item_ctx = item or db.session.get(RutaItem, ruta_item_id)
    ocupante_otro = buscar_ocupante_ot_de_otro_iniciador(
        orden_trabajo_id=orden_trabajo_id,
        iniciador_ruta_id=iniciador.id,
    )
    if ocupante_otro is not None:
        raise_orden_trabajo_ocupada_por_otro_flujo(
            orden_trabajo_id=orden_trabajo_id,
            ruta_item_id=ruta_item_id,
            ocupante=ocupante_otro,
            iniciador=iniciador,
            item=item_ctx,
            ruta=ruta,
        )

    act_reintento = buscar_actuacion_reintento_reutilizable(iniciador.id)
    conflicto = buscar_conflicto_orden_trabajo_al_publicar(
        orden_trabajo_id=orden_trabajo_id,
        ruta_item_id=ruta_item_id,
        iniciador_ruta_id=iniciador.id,
    )
    if not conflicto:
        log_publicar_debug(
            conflicto_detectado_por="validar_orden_trabajo_disponible_para_publicar",
            mensaje_conflicto=None,
            orden_trabajo_id=orden_trabajo_id,
            ruta_item_id=ruta_item_id,
            iniciador_id=iniciador.id,
            actuacion_reintento_id=act_reintento.id if act_reintento else None,
            ot_disponible=True,
        )
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
    mensaje = "".join(partes)

    item_ctx = item or RutaItem.query.get(ruta_item_id)
    debug: dict[str, Any] = {}
    if item_ctx is not None:
        debug = conflicto_ot_a_debug(
            conflicto,
            ruta=ruta,
            item=item_ctx,
            iniciador=iniciador,
        )
    debug["actuacion_reintento_id"] = act_reintento.id if act_reintento else None
    debug["actuacion_reintento_encontrada"] = act_reintento is not None

    raise_publicar_debug(
        mensaje,
        validator="buscar_conflicto_orden_trabajo_al_publicar",
        debug=debug,
    )
