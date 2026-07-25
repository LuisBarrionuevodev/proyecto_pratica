"""PR11.1d — Funciones de diagnóstico offline para publicar ruta."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database import db
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    actuacion_pertenece_iniciador,
    actuacion_reserva_orden_trabajo,
    buscar_actuacion_ocupante_orden_trabajo,
    buscar_actuacion_reintento_reutilizable,
    buscar_conflicto_orden_trabajo_al_publicar,
    resolver_actuacion_para_publicar_item,
    ruta_item_reserva_orden_trabajo,
)
from app.models import Actuaciones, IniciadorRuta, OrdenTrabajo, RutaItem, RutaTrabajo


def _iso_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _fmt_iniciador_fuentes(ini: IniciadorRuta) -> dict[str, Any]:
    return {
        "relevamiento_id": ini.relevamiento_id,
        "denuncia_id": ini.denuncia_id,
        "notificacion_id": ini.notificacion_id,
        "comprobacion_id": ini.comprobacion_id,
        "oficio_id": ini.oficio_id,
        "actuacion_id_vinculo": ini.actuacion_id,
    }


def _actuacion_candidata_row(act: Actuaciones, iniciador_id: int) -> dict[str, Any]:
    """Fila resumida de actuación candidata a reutilización."""
    ot = (
        db.session.get(OrdenTrabajo, act.orden_trabajo_id)
        if act.orden_trabajo_id
        else None
    )
    items_ini = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.actuacion_id == act.id,
        )
        .order_by(RutaItem.id.desc())
        .all()
    )
    return {
        "actuacion_id": act.id,
        "orden_trabajo_id": act.orden_trabajo_id,
        "numero_ot": ot.numero_acta if ot else None,
        "contraproducencia": act.contraproducencia,
        "notificacion_id": act.notificacion_id,
        "comprobacion_id": act.comprobacion_id,
        "mismo_iniciador": actuacion_pertenece_iniciador(act.id, iniciador_id),
        "reserva_ot": actuacion_reserva_orden_trabajo(act),
        "items_iniciador": [
            {
                "item_id": it.id,
                "estado_item": it.estado_ruta_item,
                "estado_ejecucion": it.estado_ejecucion,
                "deleted_at": _iso_dt(it.deleted_at),
                "ruta_id": it.ruta_trabajo_id,
            }
            for it in items_ini
        ],
    }


def _simular_resolver_item_borrador(
    iniciador_id: int,
    item: RutaItem,
) -> dict[str, Any]:
    """
    Simula ``resolver_actuacion_para_publicar_item`` para un ítem en borrador.

    Parámetros:
        iniciador_id: PK del iniciador.
        item: ítem borrador con OT asignada.

    Retorno:
        Informe con candidatas, decisión y bloqueos potenciales.
    """
    if not item.orden_trabajo_id:
        return {"item_id": item.id, "error": "sin_orden_trabajo_id"}

    target_ot = int(item.orden_trabajo_id)
    act_ids = {
        row[0]
        for row in db.session.query(RutaItem.actuacion_id)
        .filter(
            RutaItem.iniciador_ruta_id == iniciador_id,
            RutaItem.actuacion_id.isnot(None),
        )
        .distinct()
        .all()
    }
    candidatas: list[dict[str, Any]] = []
    for aid in sorted(act_ids, reverse=True):
        act = db.session.get(Actuaciones, aid)
        if act is None:
            continue
        row = _actuacion_candidata_row(act, iniciador_id)
        row["tiene_ot_objetivo"] = int(act.orden_trabajo_id or 0) == target_ot
        row["reusable"] = not actuacion_reserva_orden_trabajo(act)
        candidatas.append(row)

    act_ot_objetivo = next((c for c in candidatas if c["tiene_ot_objetivo"]), None)
    reintento = buscar_actuacion_reintento_reutilizable(iniciador_id)
    resolved = resolver_actuacion_para_publicar_item(
        iniciador_ruta_id=iniciador_id,
        orden_trabajo_id=target_ot,
    )
    ocupante = buscar_actuacion_ocupante_orden_trabajo(target_ot)

    decision = "crear_nueva"
    if resolved is not None:
        decision = f"reutilizar_{resolved.id}"

    bloqueo_ot: dict[str, Any] | None = None
    if ocupante is not None:
        item_occ = (
            RutaItem.query.filter(RutaItem.actuacion_id == ocupante.id)
            .order_by(RutaItem.id.desc())
            .first()
        )
        bloqueo_ot = {
            "actuacion_id": ocupante.id,
            "mismo_iniciador": actuacion_pertenece_iniciador(ocupante.id, iniciador_id),
            "iniciador_item_id": item_occ.iniciador_ruta_id if item_occ else None,
            "contraproducencia": ocupante.contraproducencia,
            "reserva_ot": actuacion_reserva_orden_trabajo(ocupante),
        }

    return {
        "item_id": item.id,
        "ruta_id": item.ruta_trabajo_id,
        "orden_trabajo_id": target_ot,
        "actuacion_con_ot_objetivo": act_ot_objetivo,
        "actuacion_reintento": reintento.id if reintento else None,
        "actuacion_resuelta_id": resolved.id if resolved else None,
        "actuacion_ocupante_ot": bloqueo_ot,
        "candidatas_reutilizables": candidatas,
        "decision": decision,
    }


def diagnosticar_iniciador_publicar(iniciador_id: int) -> dict[str, Any]:
    """
    Releva estado operativo de un iniciador para diagnosticar bloqueos al publicar.

    Parámetros:
        iniciador_id: PK de ``iniciador_ruta``.

    Retorno:
        Informe estructurado (también imprimible).
    """
    ini = db.session.get(IniciadorRuta, iniciador_id)
    if ini is None:
        return {"error": f"Iniciador {iniciador_id} no encontrado"}

    items = (
        RutaItem.query.filter(RutaItem.iniciador_ruta_id == iniciador_id)
        .order_by(RutaItem.id.asc())
        .all()
    )
    act_ids = {it.actuacion_id for it in items if it.actuacion_id}
    if ini.actuacion_id:
        act_ids.add(int(ini.actuacion_id))

    actuaciones: list[dict[str, Any]] = []
    for aid in sorted(act_ids):
        act = db.session.get(Actuaciones, aid)
        if act is None:
            continue
        ot = db.session.get(OrdenTrabajo, act.orden_trabajo_id) if act.orden_trabajo_id else None
        actuaciones.append(
            {
                "actuacion_id": act.id,
                "tipo": act.tipo,
                "contraproducencia": act.contraproducencia,
                "orden_trabajo_id": act.orden_trabajo_id,
                "numero_ot": ot.numero_acta if ot else None,
                "notificacion_id": act.notificacion_id,
                "comprobacion_id": act.comprobacion_id,
                "reserva_ot": actuacion_reserva_orden_trabajo(act),
            }
        )

    items_out: list[dict[str, Any]] = []
    for it in items:
        ruta = db.session.get(RutaTrabajo, it.ruta_trabajo_id)
        ot = db.session.get(OrdenTrabajo, it.orden_trabajo_id) if it.orden_trabajo_id else None
        items_out.append(
            {
                "item_id": it.id,
                "ruta_id": it.ruta_trabajo_id,
                "ruta_fecha": _iso_date(ruta.fecha if ruta else None),
                "estado_ruta": ruta.estado_ruta if ruta else None,
                "estado_item": it.estado_ruta_item,
                "estado_ejecucion": it.estado_ejecucion,
                "deleted_at": _iso_dt(it.deleted_at),
                "orden_trabajo_id": it.orden_trabajo_id,
                "numero_ot": ot.numero_acta if ot else None,
                "actuacion_id": it.actuacion_id,
                "reserva_ot_en_item": ruta_item_reserva_orden_trabajo(it),
            }
        )

    act_reintento = buscar_actuacion_reintento_reutilizable(iniciador_id)
    borrador_items = [
        it
        for it in items
        if it.deleted_at is None
        and (r := db.session.get(RutaTrabajo, it.ruta_trabajo_id))
        and r.estado_ruta == "BORRADOR"
    ]

    bloqueos_ot: list[dict[str, Any]] = []
    for it in borrador_items:
        if not it.orden_trabajo_id:
            continue
        ot = db.session.get(OrdenTrabajo, it.orden_trabajo_id)
        conflicto = buscar_conflicto_orden_trabajo_al_publicar(
            orden_trabajo_id=int(it.orden_trabajo_id),
            ruta_item_id=it.id,
            iniciador_ruta_id=iniciador_id,
        )
        if conflicto is not None:
            act_b = db.session.get(Actuaciones, conflicto.actuacion_id)
            bloqueos_ot.append(
                {
                    "item_borrador_id": it.id,
                    "ruta_borrador_id": it.ruta_trabajo_id,
                    "numero_ot": ot.numero_acta if ot else None,
                    "conflicto": {
                        "actuacion_bloqueante_id": conflicto.actuacion_id,
                        "item_bloqueante_id": conflicto.ruta_item_id,
                        "estado_item": conflicto.estado_ruta_item,
                        "estado_ejecucion": conflicto.estado_ejecucion,
                        "contraproducencia": act_b.contraproducencia if act_b else None,
                        "deberia_bloquear_pr11_1c": (
                            actuacion_reserva_orden_trabajo(act_b) if act_b else None
                        ),
                    },
                }
            )

    return {
        "iniciador": {
            "id": ini.id,
            "tipo": ini.tipo_iniciador,
            "estado": ini.estado_iniciador,
            "fuentes": _fmt_iniciador_fuentes(ini),
            "deleted_at": _iso_dt(ini.deleted_at),
        },
        "actuacion_reintento_detectada": act_reintento.id if act_reintento else None,
        "ruta_items": items_out,
        "actuaciones": actuaciones,
        "bloqueos_ot_en_borrador": bloqueos_ot,
        "items_borrador_activos": [it.id for it in borrador_items],
        "simulacion_resolver_borrador": [
            _simular_resolver_item_borrador(iniciador_id, it) for it in borrador_items
        ],
    }


def diagnosticar_orden_trabajo(
    *,
    orden_trabajo_id: int | None = None,
    numero: str | None = None,
    anio: int | None = None,
) -> dict[str, Any]:
    """
    Releva quién reserva una OT y qué actuaciones la usan.

    Parámetros:
        orden_trabajo_id: PK directa.
        numero: número de acta/OT (con ``anio``).
        anio: año de la OT si se busca por número.

    Retorno:
        Informe de uso de la OT.
    """
    ot: OrdenTrabajo | None = None
    if orden_trabajo_id is not None:
        ot = db.session.get(OrdenTrabajo, orden_trabajo_id)
    elif numero and anio is not None:
        ot = OrdenTrabajo.query.filter_by(numero_acta=numero, anio=anio).first()
    if ot is None:
        return {"error": "Orden de trabajo no encontrada"}

    acts = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).all()
    items = RutaItem.query.filter_by(orden_trabajo_id=ot.id).all()
    return {
        "orden_trabajo": {
            "id": ot.id,
            "numero_acta": ot.numero_acta,
            "anio": ot.anio,
            "mes": ot.mes,
        },
        "actuaciones": [
            {
                "id": a.id,
                "tipo": a.tipo,
                "contraproducencia": a.contraproducencia,
                "notificacion_id": a.notificacion_id,
                "reserva_ot": actuacion_reserva_orden_trabajo(a),
            }
            for a in acts
        ],
        "ruta_items": [
            {
                "id": it.id,
                "ruta_id": it.ruta_trabajo_id,
                "iniciador_id": it.iniciador_ruta_id,
                "estado_item": it.estado_ruta_item,
                "estado_ejecucion": it.estado_ejecucion,
                "deleted_at": _iso_dt(it.deleted_at),
                "reserva_ot": ruta_item_reserva_orden_trabajo(it),
            }
            for it in items
        ],
    }
