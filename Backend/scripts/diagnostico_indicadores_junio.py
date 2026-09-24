"""
D1d.11fix-a3-precheck — Diagnóstico junio: cierres, actas, motivos, rubros.

Uso:
    cd Backend
    set PYTHONPATH=.
    python scripts/diagnostico_indicadores_junio.py
    python scripts/diagnostico_indicadores_junio.py --desde 2026-06-01 --hasta 2026-06-30
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, exists, func

from app import create_app
from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import _loose_key
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_cierre_ruta_expr,
    actuacion_ids_realizadas_subquery,
    domicilio_id_efectivo_expr,
    query_top_rubros_cierres_realizados,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _actuacion_ids_subquery,
    _comprobacion_labarda_filter,
    _count_actas_labradas,
    _notificacion_labarda_exists,
    _normalize_motivo_label,
    query_decomiso_kg_por_rubro,
    query_top_motivos_comprobacion,
    query_top_motivos_notificacion,
)
from app.domains.indicadores.services.indicadores_riesgo_service import (
    build_indicadores_riesgo,
)
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Decomiso,
    Domicilio,
    IniciadorRuta,
    Inspeccion,
    Motivo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)
from app.models.notificacion_motivo import notificacion_motivo

_COMP_PENDIENTE = frozenset({_loose_key("PENDIENTE")})


def _base_cierres_q(desde: date, hasta: date):
    fecha_cierre = _fecha_cierre_ruta_expr()
    return (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            RutaItem.actuacion_id.label("actuacion_id"),
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.tipo_iniciador.label("tipo_iniciador"),
            IniciadorRuta.estado_iniciador.label("estado_iniciador"),
            Actuaciones.tipo.label("actuacion_tipo"),
            Actuaciones.fecha.label("actuacion_fecha"),
            Actuaciones.domicilio_id.label("act_domicilio_id"),
            IniciadorRuta.domicilio_id.label("ini_domicilio_id"),
            func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha).label(
                "fecha_cierre"
            ),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            fecha_cierre >= desde,
            fecha_cierre <= hasta,
        )
    )


def _count_actas_script(sq) -> dict[str, int]:
    """Réplica de _count_actas_labradas sobre subquery dada."""
    actas = _count_actas_labradas(sq)
    total = (
        actas.inspeccion
        + actas.notificacion
        + actas.comprobacion
        + actas.clausura
        + actas.decomiso
    )
    return {
        "inspeccion": actas.inspeccion,
        "notificacion": actas.notificacion,
        "comprobacion": actas.comprobacion,
        "clausura": actas.clausura,
        "decomiso": actas.decomiso,
        "total": total,
    }


def _motivos_notificacion_diag(sq) -> dict:
    notif_distinct = (
        db.session.query(func.count(func.distinct(Actuaciones.notificacion_id)))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Actuaciones.notificacion_id.isnot(None),
            _notificacion_labarda_exists(),
        )
        .scalar()
        or 0
    )
    motivos_total_join = (
        db.session.query(func.count(notificacion_motivo.c.motivo))
        .select_from(notificacion_motivo)
        .join(Actuaciones, Actuaciones.notificacion_id == notificacion_motivo.c.notificacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            notificacion_motivo.c.deleted_at.is_(None),
            Actuaciones.notificacion_id.isnot(None),
        )
        .scalar()
        or 0
    )
    motivos_distinct_pair = (
        db.session.query(
            func.count(
                func.distinct(
                    func.concat(
                        notificacion_motivo.c.notificacion_id,
                        "-",
                        notificacion_motivo.c.motivo,
                    )
                )
            )
        )
        .select_from(notificacion_motivo)
        .join(Actuaciones, Actuaciones.notificacion_id == notificacion_motivo.c.notificacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            notificacion_motivo.c.deleted_at.is_(None),
            Actuaciones.notificacion_id.isnot(None),
        )
        .scalar()
        or 0
    )
    motivos_con_inspector_join = (
        db.session.query(func.count(notificacion_motivo.c.motivo))
        .select_from(notificacion_motivo)
        .join(Actuaciones, Actuaciones.notificacion_id == notificacion_motivo.c.notificacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        )
        .filter(
            notificacion_motivo.c.deleted_at.is_(None),
            actuaciones_inspector.c.deleted_at.is_(None),
            Actuaciones.notificacion_id.isnot(None),
        )
        .scalar()
        or 0
    )
    top_rows = (
        db.session.query(
            Motivo.nombre,
            func.count(notificacion_motivo.c.motivo),
            func.count(func.distinct(Actuaciones.notificacion_id)),
        )
        .select_from(notificacion_motivo)
        .join(Actuaciones, Actuaciones.notificacion_id == notificacion_motivo.c.notificacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .join(Motivo, Motivo.id == notificacion_motivo.c.motivo)
        .filter(
            notificacion_motivo.c.deleted_at.is_(None),
            Actuaciones.notificacion_id.isnot(None),
            Motivo.nombre.isnot(None),
            func.trim(Motivo.nombre) != "",
        )
        .group_by(Motivo.id, Motivo.nombre)
        .order_by(func.count(notificacion_motivo.c.motivo).desc())
        .limit(15)
        .all()
    )
    promedio = (
        float(motivos_total_join) / notif_distinct if notif_distinct else 0.0
    )
    return {
        "notificaciones_labradas": int(notif_distinct),
        "motivos_total_join": int(motivos_total_join),
        "motivos_distinct_notif_motivo_pair": int(motivos_distinct_pair),
        "motivos_con_join_inspector": int(motivos_con_inspector_join),
        "duplicacion_por_inspector": int(motivos_con_inspector_join)
        - int(motivos_total_join),
        "promedio_motivos_por_notificacion": round(promedio, 2),
        "top_motivos": [
            {
                "motivo": _normalize_motivo_label(str(n)),
                "cantidad_motivos": int(cnt),
                "notificaciones_distinct": int(nd),
            }
            for n, cnt, nd in top_rows
        ],
    }


def _motivos_comprobacion_diag(sq) -> dict:
    comp_distinct = (
        db.session.query(func.count(func.distinct(Actuaciones.comprobacion_id)))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(_comprobacion_labarda_filter())
        .scalar()
        or 0
    )
    comp_con_motivo_raw = (
        db.session.query(func.count(Comprobacion.id))
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.isnot(None),
            func.trim(Comprobacion.motivo) != "",
        )
        .scalar()
        or 0
    )
    pendiente = (
        db.session.query(func.count(Comprobacion.id))
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Comprobacion.deleted_at.is_(None),
            func.upper(func.trim(Comprobacion.motivo)) == "PENDIENTE",
        )
        .scalar()
        or 0
    )
    vacios = (
        db.session.query(func.count(Comprobacion.id))
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.is_(None) | (func.trim(Comprobacion.motivo) == ""),
        )
        .scalar()
        or 0
    )
    comp_con_inspector = (
        db.session.query(func.count(Comprobacion.id))
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        )
        .filter(
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.isnot(None),
            func.trim(Comprobacion.motivo) != "",
            Comprobacion.motivo != "PENDIENTE",
            actuaciones_inspector.c.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    top_rows = (
        db.session.query(
            Comprobacion.motivo,
            func.count(Comprobacion.id),
            func.count(func.distinct(Comprobacion.id)),
        )
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.isnot(None),
            func.trim(Comprobacion.motivo) != "",
            func.upper(func.trim(Comprobacion.motivo)) != "PENDIENTE",
        )
        .group_by(Comprobacion.motivo)
        .order_by(func.count(Comprobacion.id).desc())
        .limit(15)
        .all()
    )
    return {
        "comprobaciones_labradas": int(comp_distinct),
        "motivos_comprobacion_validos_query": int(comp_con_motivo_raw)
        - int(pendiente)
        - int(vacios),
        "pendiente_excluidos": int(pendiente),
        "vacios_excluidos": int(vacios),
        "con_join_inspector": int(comp_con_inspector),
        "duplicacion_por_inspector": int(comp_con_inspector) - int(comp_distinct),
        "top_motivos": [
            {
                "motivo": _normalize_motivo_label(str(m)),
                "cantidad": int(cnt),
                "comprobaciones_distinct": int(cd),
            }
            for m, cnt, cd in top_rows
        ],
    }


def _rubros_diag(rows: list, desde: date, hasta: date) -> dict:
    act_ids = {r.actuacion_id for r in rows}
    ruta_items = len(rows)

    con_act_dom = sum(1 for r in rows if r.act_domicilio_id)
    con_ini_dom = sum(1 for r in rows if r.ini_domicilio_id)
    dom_eff_ids = [
        r.act_domicilio_id or r.ini_domicilio_id for r in rows
    ]
    con_dom_eff = sum(1 for d in dom_eff_ids if d)

    rubro_act: dict[str, int] = defaultdict(int)
    rubro_ini: dict[str, int] = defaultdict(int)
    rubro_eff_ruta: dict[str, int] = defaultdict(int)
    rubro_eff_act: dict[str, int] = defaultdict(int)
    sin_rubro = 0
    recuperables = 0

    dom_cache: dict[int, tuple[int | None, str | None]] = {}

    def _dom_info(dom_id: int | None):
        if dom_id is None:
            return None, None
        if dom_id not in dom_cache:
            d = Domicilio.query.get(dom_id)
            if d is None:
                dom_cache[dom_id] = (None, None)
            else:
                rub = Rubro.query.get(d.rubro_id) if d.rubro_id else None
                dom_cache[dom_id] = (d.rubro_id, rub.nombre if rub else None)
        return dom_cache[dom_id]

    for r in rows:
        rid_act, nom_act = _dom_info(r.act_domicilio_id)
        rid_ini, nom_ini = _dom_info(r.ini_domicilio_id)
        if rid_act and nom_act:
            rubro_act[nom_act] += 1
        if rid_ini and nom_ini:
            rubro_ini[nom_ini] += 1
        eff_id = r.act_domicilio_id or r.ini_domicilio_id
        rid_eff, nom_eff = _dom_info(eff_id)
        if rid_eff and nom_eff:
            rubro_eff_ruta[nom_eff] += 1
        else:
            sin_rubro += 1
        if not rid_act and rid_ini:
            recuperables += 1

    # fix rubro_eff_act - count distinct actuacion per rubro
    rubro_eff_act = defaultdict(int)
    seen_act_rubro: set[tuple[int, str]] = set()
    for r in rows:
        eff_id = r.act_domicilio_id or r.ini_domicilio_id
        _, nom_eff = _dom_info(eff_id)
        if nom_eff:
            key = (r.actuacion_id, nom_eff)
            if key not in seen_act_rubro:
                seen_act_rubro.add(key)
                rubro_eff_act[nom_eff] += 1

    sq = actuacion_ids_realizadas_subquery(desde, hasta)
    top_service = query_top_rubros_cierres_realizados(desde, hasta, limit=15)

    return {
        "ruta_items_realizados": ruta_items,
        "actuaciones_distinct": len(act_ids),
        "con_domicilio_actuacion": con_act_dom,
        "con_domicilio_iniciador": con_ini_dom,
        "con_domicilio_efectivo": con_dom_eff,
        "sin_rubro_efectivo": sin_rubro,
        "con_rubro_actuacion": sum(rubro_act.values()),
        "con_rubro_iniciador": sum(rubro_ini.values()),
        "recuperables_por_fallback_ini": recuperables,
        "top_rubros_por_ruta_item": dict(
            sorted(rubro_eff_ruta.items(), key=lambda x: -x[1])[:15]
        ),
        "top_rubros_por_actuacion_distinct": dict(
            sorted(rubro_eff_act.items(), key=lambda x: -x[1])[:15]
        ),
        "top_rubros_service": [
            {"rubro_id": rid, "nombre": nom, "count": cnt} for rid, nom, cnt in top_service
        ],
        "sq_actuaciones_count": int(
            db.session.query(func.count()).select_from(sq).scalar() or 0
        ),
    }


def run(desde: date, hasta: date) -> dict:
    rows = _base_cierres_q(desde, hasta).all()
    sq_cierre = actuacion_ids_realizadas_subquery(desde, hasta)
    sq_fecha_cruda = _actuacion_ids_subquery(desde, hasta, None, None)

    # B — base cierres
    tabla_cruce: dict[tuple, dict] = defaultdict(
        lambda: {"ruta_items": 0, "actuaciones": set()}
    )
    inconsistencias: list[dict] = []
    estado_ini_agg: dict[tuple, int] = defaultdict(int)

    for r in rows:
        key = (
            str(r.tipo_iniciador),
            str(r.estado_iniciador),
            str(r.actuacion_tipo),
        )
        tabla_cruce[key]["ruta_items"] += 1
        tabla_cruce[key]["actuaciones"].add(r.actuacion_id)
        estado_ini_agg[(str(r.estado_iniciador), str(r.tipo_iniciador))] += 1
        est = str(r.estado_iniciador).upper()
        if est not in ("CUMPLIDO", "CERRADO", "FINALIZADO") and "CUMPL" not in est:
            inconsistencias.append(
                {
                    "ruta_item_id": r.ruta_item_id,
                    "iniciador_id": r.iniciador_id,
                    "estado_iniciador": r.estado_iniciador,
                    "tipo_iniciador": r.tipo_iniciador,
                    "actuacion_tipo": r.actuacion_tipo,
                }
            )

    tabla1 = [
        {
            "tipo_iniciador": k[0],
            "estado_iniciador": k[1],
            "actuaciones_tipo": k[2],
            "ruta_items": v["ruta_items"],
            "actuaciones_distinct": len(v["actuaciones"]),
        }
        for k, v in sorted(tabla_cruce.items(), key=lambda x: -x[1]["ruta_items"])
    ]

    por_ini = defaultdict(int)
    por_act = defaultdict(int)
    for r in rows:
        por_ini[str(r.tipo_iniciador)] += 1
        por_act[str(r.actuacion_tipo)] += 1

    # C — actas labradas
    actas_script = _count_actas_script(sq_cierre)
    ejecutivo = build_indicadores_ejecutivo(desde, hasta)
    ep_actas = ejecutivo.actas_por_tipo
    actas_endpoint = {
        "inspeccion": ep_actas.inspeccion,
        "notificacion": ep_actas.notificacion,
        "comprobacion": ep_actas.comprobacion,
        "clausura": ep_actas.clausura,
        "decomiso": ep_actas.decomiso,
        "total": (
            ep_actas.inspeccion
            + ep_actas.notificacion
            + ep_actas.comprobacion
            + ep_actas.clausura
            + ep_actas.decomiso
        ),
    }
    actas_compare = {
        tipo: {
            "script": actas_script[tipo],
            "endpoint": actas_endpoint[tipo],
            "diferencia": actas_endpoint[tipo] - actas_script[tipo],
        }
        for tipo in actas_script
    }

    # Actas con fecha cruda (resumen legacy)
    actas_fecha_cruda = _count_actas_script(sq_fecha_cruda)

    # D/E — motivos
    mot_notif = _motivos_notificacion_diag(sq_cierre)
    mot_comp = _motivos_comprobacion_diag(sq_cierre)

    # F — rubros
    rubros = _rubros_diag(rows, desde, hasta)

    # G — riesgo vs script
    riesgo = build_indicadores_riesgo(desde, hasta)
    mot_notif_svc = query_top_motivos_notificacion(desde, hasta, limit=15)
    mot_comp_svc = query_top_motivos_comprobacion(desde, hasta, limit=15)
    decomiso_svc = query_decomiso_kg_por_rubro(desde, hasta)

    def _dict_top(items, key_name="cantidad"):
        return {getattr(i, "rubro" if hasattr(i, "rubro") else "motivo"): getattr(i, key_name if hasattr(i, key_name) else "kg") for i in items}

    riesgo_compare = []
    for item in riesgo.top_rubros:
        script_val = rubros["top_rubros_por_ruta_item"].get(item.rubro, 0)
        riesgo_compare.append(
            {
                "indicador": f"top_rubros:{item.rubro}",
                "endpoint": item.cantidad,
                "script": script_val,
                "diferencia": item.cantidad - script_val,
                "posible_causa": "ok" if item.cantidad == script_val else "revisar join/distinct",
            }
        )
    for item in riesgo.top_motivos_notificacion:
        script_val = next(
            (m["cantidad_motivos"] for m in mot_notif["top_motivos"] if m["motivo"] == item.motivo),
            0,
        )
        riesgo_compare.append(
            {
                "indicador": f"top_motivos_notificacion:{item.motivo}",
                "endpoint": item.cantidad,
                "script": script_val,
                "diferencia": item.cantidad - script_val,
                "posible_causa": "motivos por acta (no actas)" if script_val else "sin match",
            }
        )
    for item in riesgo.top_motivos_comprobacion:
        script_val = next(
            (m["cantidad"] for m in mot_comp["top_motivos"] if m["motivo"] == item.motivo),
            0,
        )
        riesgo_compare.append(
            {
                "indicador": f"top_motivos_comprobacion:{item.motivo}",
                "endpoint": item.cantidad,
                "script": script_val,
                "diferencia": item.cantidad - script_val,
                "posible_causa": "ok" if item.cantidad == script_val else "revisar",
            }
        )

    # H — fecha cruda vs cierre
    n_fecha_cruda = int(
        db.session.query(func.count()).select_from(sq_fecha_cruda).scalar() or 0
    )
    n_cierre = int(db.session.query(func.count()).select_from(sq_cierre).scalar() or 0)

    ids_cierre = {r[0] for r in db.session.query(sq_cierre.c.id).all()}
    actuaciones_solo_fecha_cruda = (
        db.session.query(func.count(Actuaciones.id))
        .filter(
            Actuaciones.fecha >= desde,
            Actuaciones.fecha <= hasta,
            ~Actuaciones.id.in_(ids_cierre) if ids_cierre else True,
        )
        .scalar()
        or 0
    )
    actuaciones_solo_cierre = (
        db.session.query(func.count(func.distinct(sq_cierre.c.id)))
        .select_from(sq_cierre)
        .outerjoin(Actuaciones, Actuaciones.id == sq_cierre.c.id)
        .filter(
            (Actuaciones.fecha < desde) | (Actuaciones.fecha > hasta) | Actuaciones.fecha.is_(None)
        )
        .scalar()
        or 0
    )

    # Resumen endpoint usa fecha cruda para top rubros interno
    rubros_resumen_fecha = (
        db.session.query(Rubro.nombre, func.count(Actuaciones.id))
        .join(sq_fecha_cruda, sq_fecha_cruda.c.id == Actuaciones.id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .join(Rubro, Rubro.id == Domicilio.rubro_id)
        .group_by(Rubro.id, Rubro.nombre)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(10)
        .all()
    )

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "B_base_cierres": {
            "ruta_items_realizados": len(rows),
            "actuaciones_distinct": len({r.actuacion_id for r in rows}),
            "iniciadores_distinct": len({r.iniciador_id for r in rows}),
            "por_tipo_iniciador": dict(sorted(por_ini.items(), key=lambda x: -x[1])),
            "por_actuaciones_tipo": dict(sorted(por_act.items(), key=lambda x: -x[1])),
            "tabla_cruce": tabla1,
            "estado_iniciador_x_tipo": [
                {"estado_iniciador": k[0], "tipo_iniciador": k[1], "cierres": v}
                for k, v in sorted(estado_ini_agg.items(), key=lambda x: -x[1])
            ],
            "inconsistencias_realizado_sin_cumplido": inconsistencias[:30],
            "total_inconsistencias": len(inconsistencias),
        },
        "C_actas_labradas": {
            "por_tipo_cierre_script": actas_script,
            "por_tipo_endpoint_ejecutivo": actas_endpoint,
            "comparacion": actas_compare,
            "actas_con_fecha_cruda_resumen": actas_fecha_cruda,
            "kpis_ejecutivo": {
                "actuaciones_realizadas": ejecutivo.kpis.actuaciones_realizadas,
                "actas_labradas": ejecutivo.kpis.actas_labradas,
            },
        },
        "D_motivos_notificacion": mot_notif,
        "E_motivos_comprobacion": mot_comp,
        "F_rubros": rubros,
        "G_riesgo_endpoint": {
            "top_rubros": [{"rubro": i.rubro, "cantidad": i.cantidad} for i in riesgo.top_rubros],
            "top_motivos_notificacion": [
                {"motivo": i.motivo, "cantidad": i.cantidad}
                for i in riesgo.top_motivos_notificacion
            ],
            "top_motivos_comprobacion": [
                {"motivo": i.motivo, "cantidad": i.cantidad}
                for i in riesgo.top_motivos_comprobacion
            ],
            "decomiso_kg_por_rubro": [
                {"rubro": i.rubro, "kg": i.kg} for i in riesgo.decomiso_kg_por_rubro
            ],
            "comparacion": riesgo_compare,
            "service_queries": {
                "top_motivos_notificacion": mot_notif_svc,
                "top_motivos_comprobacion": mot_comp_svc,
                "decomiso_kg": decomiso_svc,
            },
        },
        "H_queries_audit": {
            "actuaciones_fecha_cruda_junio": n_fecha_cruda,
            "actuaciones_cierre_junio": n_cierre,
            "solo_en_fecha_cruda_no_en_cierre": int(actuaciones_solo_fecha_cruda),
            "solo_en_cierre_fuera_fecha_actuacion": int(actuaciones_solo_cierre),
            "resumen_top_rubros_usa_fecha_cruda": [
                {"rubro": str(n), "count": int(c)} for n, c in rubros_resumen_fecha
            ],
            "riesgo_top_rubros_usa_cierre": [
                {"rubro": nom, "count": cnt}
                for _rid, nom, cnt in query_top_rubros_cierres_realizados(desde, hasta, limit=10)
            ],
            "notas": [
                "ejecutivo/riesgo motivos y rubros usan actuacion_ids_realizadas_subquery (cierre)",
                "resumen total actuaciones y top_rubros interno usan _actuacion_ids_subquery (Actuaciones.fecha)",
                "query_top_motivos_notificacion cuenta filas notificacion_motivo, no actas",
                "query_top_motivos_comprobacion agrupa por motivo texto; 1 motivo por comprobacion",
            ],
        },
        "I_estado_iniciador": {
            "agrupado": [
                {"estado_iniciador": k[0], "tipo_iniciador": k[1], "cierres_realizados": v}
                for k, v in sorted(estado_ini_agg.items(), key=lambda x: -x[1])
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default="2026-06-01")
    parser.add_argument("--hasta", default="2026-06-30")
    args = parser.parse_args()
    desde = date.fromisoformat(args.desde)
    hasta = date.fromisoformat(args.hasta)

    app = create_app()
    with app.app_context():
        out = run(desde, hasta)
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
