from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_efectivo_para_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    _actuacion_puede_reutilizarse_en_publicacion,
    actuacion_pertenece_iniciador,
    buscar_actuacion_ocupante_orden_trabajo,
    buscar_actuacion_reintento_reutilizable,
    evaluar_actuacion_para_publicar_item,
    raise_orden_trabajo_ocupada_por_otro_flujo,
    validar_orden_trabajo_disponible_para_publicar,
)
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import (
    log_before_commit_publicar_ruta,
    log_publicar_debug,
    parse_integrity_error,
    raise_publicar_debug,
    snapshot_item_publicar_context,
)
from app.models import Actuaciones, RutaGrupo, RutaItem, RutaTrabajo


def tipo_actuacion_para_iniciador(tipo_iniciador: str) -> str:
    """
    Mapea `IniciadorRuta.tipo_iniciador` al string de `Actuaciones.tipo` alineado al catálogo
    (`CatalogTipoActuacion` / valores usados en grilla).

    Parámetros:
        tipo_iniciador: valor del enum en `iniciador_ruta.tipo_iniciador`.

    Retorno:
        Nombre de tipo de actuación persistible en `actuaciones.tipo`.

    Errores:
        KeyError: si el tipo no está contemplado (no debería ocurrir con datos válidos de DB).
    """
    mapping: dict[str, str] = {
        "RELEVAMIENTO": "INSPECCION",
        "DENUNCIA": "INSPECCION",
        "REINSPECCION_OFICIO": "REINSPECCION",
        "REINSPECCION_NOTIFICACION": "REINSPECCION",
        "VERIFICAR_INFORMAR_OFICIO": "VERIFICAR E INFORMAR",
        "RATIFICACION_CLAUSURA_OFICIO": "RATIFICACION DE CLAUSURA",
        "RATIFICACION_DECOMISO_OFICIO": "RATIFICACION DE DECOMISO",
    }
    if tipo_iniciador not in mapping:
        raise KeyError(f"tipo_iniciador no mapeado a actuación: {tipo_iniciador!r}")
    return mapping[tipo_iniciador]


def _asignar_orden_trabajo_segura(
    act: Actuaciones,
    *,
    orden_trabajo_id: int,
    iniciador_ruta_id: int,
    ruta_item_id: int,
) -> Actuaciones:
    """
    Asigna OT a una actuación reutilizada sin violar el índice único.

    Si la OT ya está en otra actuación del mismo iniciador, devuelve esa fila.
    Si está en otro flujo, lanza 409 explícito.

    Parámetros:
        act: actuación candidata a reutilizar.
        orden_trabajo_id: OT del ítem en publicación.
        iniciador_ruta_id: iniciador del ítem.
        ruta_item_id: ítem en publicación (debug).

    Retorno:
        Actuación que debe persistirse (puede ser distinta de ``act``).

    Errores:
        RutaPublicarDebugError: OT ocupada por otro flujo.
    """
    target_ot = int(orden_trabajo_id)
    if int(act.orden_trabajo_id or 0) == target_ot:
        return act

    ocupante = buscar_actuacion_ocupante_orden_trabajo(
        target_ot,
        excluir_actuacion_id=act.id,
    )
    if ocupante is None:
        act.orden_trabajo_id = target_ot
        return act

    if actuacion_pertenece_iniciador(ocupante.id, iniciador_ruta_id):
        return ocupante

    raise_orden_trabajo_ocupada_por_otro_flujo(
        orden_trabajo_id=target_ot,
        ruta_item_id=ruta_item_id,
        ocupante=ocupante,
        extra_debug={
            "actuacion_reutilizar_id": act.id,
            "iniciador_id": iniciador_ruta_id,
        },
    )


def publicar_ruta_trabajo(*, ruta_id: int) -> tuple[RutaTrabajo, list[RutaItem]]:
    """
    Publica una ruta en BORRADOR: valida grupos/ítems/OT, crea una actuación mínima por ítem
    activo, actualiza estados y persiste en una única transacción.

    Parámetros:
        ruta_id: identificador de `ruta_trabajo`.

    Retorno:
        Tupla `(ruta, items_activos_actualizados)` tras el commit.

    Errores:
        LookupError: ruta inexistente.
        RuntimeError: reglas de negocio no cumplidas (estado, inspectores, ítems, OT, duplicados,
        tipo de iniciador sin mapeo).
    """
    ruta = RutaTrabajo.query.filter(RutaTrabajo.id == ruta_id).with_for_update().first()
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")

    log_publicar_debug(
        conflicto_detectado_por="publicar_ruta_trabajo.inicio",
        ruta_id=ruta.id,
        ruta_fecha=ruta.fecha.isoformat(),
        estado_ruta=ruta.estado_ruta,
    )

    if ruta.estado_ruta != "BORRADOR":
        raise_publicar_debug(
            "La ruta debe estar en estado BORRADOR para publicar",
            validator="publicar_ruta_trabajo.estado_ruta",
            debug={"ruta_id": ruta.id, "estado_ruta": ruta.estado_ruta},
        )

    grupos = (
        RutaGrupo.query.filter(
            RutaGrupo.ruta_trabajo_id == ruta.id,
            RutaGrupo.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaGrupo.grupo_inspectores),
            joinedload(RutaGrupo.items).joinedload(RutaItem.iniciador_ruta),
            joinedload(RutaGrupo.items).joinedload(RutaItem.orden_trabajo),
        )
        .order_by(RutaGrupo.id.asc())
        .all()
    )

    if not grupos:
        raise_publicar_debug(
            "La ruta debe tener al menos un grupo activo para publicar",
            validator="publicar_ruta_trabajo.sin_grupos",
            debug={"ruta_id": ruta.id},
        )

    for grupo in grupos:
        n_insp = len(grupo.grupo_inspectores or [])
        if n_insp < 2:
            raise_publicar_debug(
                f"El grupo «{grupo.nombre}» debe tener al menos 2 inspectores asignados",
                validator="publicar_ruta_trabajo.inspectores_grupo",
                debug={"ruta_id": ruta.id, "grupo_id": grupo.id, "inspectores": n_insp},
            )
        n_items_activos = sum(1 for it in (grupo.items or []) if it.deleted_at is None)
        if n_items_activos < 1:
            raise_publicar_debug(
                f"El grupo «{grupo.nombre}» debe tener al menos un trabajo (ítem) activo",
                validator="publicar_ruta_trabajo.sin_items_grupo",
                debug={"ruta_id": ruta.id, "grupo_id": grupo.id},
            )

    items_activos = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.deleted_at.is_(None),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta),
            joinedload(RutaItem.orden_trabajo),
        )
        .order_by(RutaItem.id.asc())
        .all()
    )

    if not items_activos:
        raise_publicar_debug(
            "No hay trabajos activos en la ruta para publicar",
            validator="publicar_ruta_trabajo.sin_items",
            debug={"ruta_id": ruta.id},
        )

    for item in items_activos:
        ini = item.iniciador_ruta
        ctx = snapshot_item_publicar_context(ruta=ruta, item=item, iniciador=ini)
        if item.ruta_grupo_id is None:
            raise_publicar_debug(
                f"El ítem {item.id} no está asignado a un grupo",
                validator="publicar_ruta_trabajo.item_sin_grupo",
                debug=ctx,
            )
        if item.orden_trabajo_id is None:
            raise_publicar_debug(
                f"El ítem {item.id} no tiene Orden de Trabajo cargada",
                validator="publicar_ruta_trabajo.item_sin_ot",
                debug=ctx,
            )
        if item.estado_ruta_item != "ASIGNADO":
            raise_publicar_debug(
                f"El ítem {item.id} no está en estado ASIGNADO (estado actual: {item.estado_ruta_item})",
                validator="publicar_ruta_trabajo.item_estado_invalido",
                debug=ctx,
            )
        if item.actuacion_id is not None:
            raise_publicar_debug(
                f"El ítem {item.id} ya tiene actuación asociada",
                validator="publicar_ruta_trabajo.item_con_actuacion",
                debug=ctx,
            )
        if not ini:
            raise_publicar_debug(
                f"El ítem {item.id} no tiene iniciador asociado",
                validator="publicar_ruta_trabajo.item_sin_iniciador",
                debug=ctx,
            )
        if ini.deleted_at is not None:
            raise_publicar_debug(
                f"El iniciador {ini.id} del ítem {item.id} está eliminado",
                validator="publicar_ruta_trabajo.iniciador_eliminado",
                debug=ctx,
            )
        if ini.estado_iniciador != "PLANIFICADO":
            raise_publicar_debug(
                f"El iniciador {ini.id} debe estar PLANIFICADO para publicar (actual: {ini.estado_iniciador})",
                validator="publicar_ruta_trabajo.iniciador_estado_invalido",
                debug=ctx,
            )

        log_publicar_debug(
            conflicto_detectado_por="publicar_ruta_trabajo.pre_validar_ot",
            mensaje_conflicto=None,
            **ctx,
        )
        validar_orden_trabajo_disponible_para_publicar(
            orden_trabajo_id=int(item.orden_trabajo_id),
            ruta_item_id=item.id,
            iniciador=ini,
            ruta=ruta,
            item=item,
        )

    fecha = ruta.fecha
    mes = int(fecha.month)
    anio = int(fecha.year)

    try:
        items_debug: list[dict] = []
        for item in items_activos:
            ini = item.iniciador_ruta
            assert ini is not None
            ctx = snapshot_item_publicar_context(ruta=ruta, item=item, iniciador=ini)
            item_actuacion_id_antes = item.actuacion_id
            act_previa = buscar_actuacion_reintento_reutilizable(ini.id)
            try:
                tipo_act = tipo_actuacion_para_iniciador(ini.tipo_iniciador)
            except KeyError as exc:
                raise_publicar_debug(
                    str(exc),
                    validator="publicar_ruta_trabajo.tipo_iniciador_sin_mapeo",
                    debug=ctx,
                    cause=exc,
                )

            efectivo = resolve_domicilio_efectivo_para_iniciador(
                ini,
                apply_backfill=True,
                try_sync=True,
            )
            domicilio_publicar = efectivo.domicilio_id or ini.domicilio_id
            if not domicilio_publicar:
                raise_publicar_debug(
                    f"El iniciador {ini.id} no tiene domicilio efectivo para publicar la ruta",
                    validator="publicar_ruta_trabajo.sin_domicilio",
                    debug=ctx,
                )

            act_resuelta = evaluar_actuacion_para_publicar_item(
                iniciador_ruta_id=ini.id,
                orden_trabajo_id=int(item.orden_trabajo_id),
                ruta_item_id=item.id,
                iniciador=ini,
                item=item,
                ruta=ruta,
            )
            modo = "reutilizar" if act_resuelta is not None else "crear"

            if act_resuelta is not None:
                log_publicar_debug(
                    conflicto_detectado_por="publicar_ruta_trabajo.reutilizar_actuacion",
                    mensaje_conflicto=None,
                    reutiliza_actuacion=True,
                    actuacion_reutilizar_id=act_resuelta.id,
                    actuacion_reutilizar_orden_trabajo_id=act_resuelta.orden_trabajo_id,
                    **ctx,
                )
                act = db.session.get(Actuaciones, act_resuelta.id)
                if act is None:
                    raise_publicar_debug(
                        f"Actuación reutilizable {act_resuelta.id} no encontrada",
                        validator="publicar_ruta_trabajo.actuacion_reutilizable_inexistente",
                        debug=ctx,
                    )
                act_ot_antes = act.orden_trabajo_id
                act = _asignar_orden_trabajo_segura(
                    act,
                    orden_trabajo_id=int(item.orden_trabajo_id),
                    iniciador_ruta_id=ini.id,
                    ruta_item_id=item.id,
                )
                act.fecha = fecha
                act.mes = mes
                act.anio = anio
                act.tipo = tipo_act
                act.contraproducencia = None
                act.domicilio_id = int(domicilio_publicar)
                act.notificacion_id = (
                    ini.notificacion_id
                    if ini.tipo_iniciador == "REINSPECCION_NOTIFICACION"
                    else None
                )
                act.resultado_cumplimiento_oficio = None
                db.session.add(act)
                db.session.flush()
            else:
                log_publicar_debug(
                    conflicto_detectado_por="publicar_ruta_trabajo.crear_actuacion_nueva",
                    mensaje_conflicto=None,
                    reutiliza_actuacion=False,
                    **ctx,
                )
                ocupante_global = buscar_actuacion_ocupante_orden_trabajo(
                    int(item.orden_trabajo_id)
                )
                if ocupante_global is not None:
                    if actuacion_pertenece_iniciador(ocupante_global.id, ini.id) and _actuacion_puede_reutilizarse_en_publicacion(
                        ocupante_global, ini.id
                    ):
                        act = ocupante_global
                        act_ot_antes = act.orden_trabajo_id
                        modo = "reutilizar_ocupante_global"
                        act.fecha = fecha
                        act.mes = mes
                        act.anio = anio
                        act.tipo = tipo_act
                        act.contraproducencia = None
                        act.domicilio_id = int(domicilio_publicar)
                        act.notificacion_id = (
                            ini.notificacion_id
                            if ini.tipo_iniciador == "REINSPECCION_NOTIFICACION"
                            else None
                        )
                        act.resultado_cumplimiento_oficio = None
                        db.session.add(act)
                        db.session.flush()
                    else:
                        raise_orden_trabajo_ocupada_por_otro_flujo(
                            orden_trabajo_id=int(item.orden_trabajo_id),
                            ruta_item_id=item.id,
                            ocupante=ocupante_global,
                            iniciador=ini,
                            item=item,
                            ruta=ruta,
                        )
                else:
                    act = Actuaciones(
                        fecha=fecha,
                        mes=mes,
                        anio=anio,
                        tipo=tipo_act,
                        contraproducencia=None,
                        orden_trabajo_id=item.orden_trabajo_id,
                        domicilio_id=int(domicilio_publicar),
                        notificacion_id=(
                            ini.notificacion_id
                            if ini.tipo_iniciador == "REINSPECCION_NOTIFICACION"
                            else None
                        ),
                    )
                    act_ot_antes = None
                    db.session.add(act)
                    db.session.flush()

            item.actuacion_id = act.id
            item.estado_ruta_item = "EN_PROCESO"
            ini.estado_iniciador = "EN_EJECUCION"

            items_debug.append(
                {
                    "item_id": item.id,
                    "iniciador_id": ini.id,
                    "orden_trabajo_id": item.orden_trabajo_id,
                    "numero_orden_trabajo": ctx.get("numero_orden_trabajo"),
                    "actuacion_resuelta_id": act_resuelta.id if act_resuelta else None,
                    "actuacion_previa_id": act_previa.id if act_previa else None,
                    "actuacion_a_usar_id": act.id,
                    "modo_persistencia": modo,
                    "item_actuacion_id_antes": item_actuacion_id_antes,
                    "item_actuacion_id_despues": item.actuacion_id,
                    "act_orden_trabajo_id_antes": act_ot_antes,
                    "act_orden_trabajo_id_despues": act.orden_trabajo_id,
                }
            )

        log_before_commit_publicar_ruta(ruta_id=ruta.id, items_debug=items_debug)
        ruta.estado_ruta = "PUBLICADA"
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        item_ctx = None
        if items_activos:
            last = items_activos[-1]
            ini_last = last.iniciador_ruta
            item_ctx = snapshot_item_publicar_context(
                ruta=ruta, item=last, iniciador=ini_last
            )
        debug = parse_integrity_error(exc)
        if item_ctx:
            debug.update(item_ctx)
        debug["fase"] = "commit_publicar_ruta"
        raise_publicar_debug(
            f"Conflicto de integridad al publicar: {debug.get('message', exc)}",
            validator="IntegrityError_commit_publicar",
            debug=debug,
            cause=exc,
        )
    except Exception:
        db.session.rollback()
        raise

    return ruta, items_activos
