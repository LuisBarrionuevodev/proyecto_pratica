"""
D1d.11fix-a3-precheck2 — Trazabilidad Completar trabajo y fecha de cierre.

Uso:
    cd Backend
    set PYTHONPATH=.
    python scripts/diagnostico_completar_trabajo_junio.py
    python scripts/diagnostico_completar_trabajo_junio.py --desde 2026-06-01 --hasta 2026-06-30
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy import func

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_ejecutado_auditoria_expr,
    _fecha_periodo_operativo_expr,
    count_cierres_realizados,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    _no_realizadas_base_query,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta, Rubro, RutaItem, RutaTrabajo

# Actuaciones que el usuario pegó de junio (702–763).
_ACTUACIONES_USUARIO = list(range(702, 764))


def _dt_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.date().isoformat()


def _in_range(d: date | None, desde: date, hasta: date) -> bool:
    return d is not None and desde <= d <= hasta


def _base_realizados_q():
    """Candidatos operativos: PUBLICADA + FINALIZADO + REALIZADO + actuacion_id."""
    return (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            RutaItem.ruta_trabajo_id,
            RutaItem.estado_ruta_item,
            RutaItem.estado_ejecucion,
            RutaItem.ejecutado_at,
            RutaItem.created_at.label("ri_created_at"),
            RutaItem.updated_at.label("ri_updated_at"),
            RutaItem.actuacion_id,
            RutaTrabajo.fecha.label("ruta_fecha"),
            RutaTrabajo.estado_ruta,
            Actuaciones.fecha.label("act_fecha"),
            Actuaciones.created_at.label("act_created_at"),
            Actuaciones.updated_at.label("act_updated_at"),
            Actuaciones.tipo.label("act_tipo"),
            Actuaciones.contraproducencia,
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.tipo_iniciador,
            IniciadorRuta.estado_iniciador,
            IniciadorRuta.created_at.label("ini_created_at"),
            IniciadorRuta.updated_at.label("ini_updated_at"),
            Domicilio.calle,
            Domicilio.numero,
            Rubro.nombre.label("rubro_nombre"),
            _fecha_periodo_operativo_expr().label("fecha_ruta_periodo"),
            _fecha_ejecutado_auditoria_expr().label("fecha_cierre_auditoria"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
        )
    )


def _row_flags(row, desde: date, hasta: date) -> dict[str, bool]:
    fc = row.fecha_ruta_periodo
    ej = row.ejecutado_at.date() if row.ejecutado_at else None
    fa = row.fecha_cierre_auditoria
    ri_upd = row.ri_updated_at.date() if row.ri_updated_at else None
    act_cr = row.act_created_at.date() if row.act_created_at else None
    act_f = row.act_fecha
    ini_upd = row.ini_updated_at.date() if row.ini_updated_at else None
    ini_cumplido = str(row.estado_iniciador) == "CUMPLIDO"

    return {
        "entra_criterio_periodo_ruta": _in_range(fc, desde, hasta),
        "entra_ejecutado_at": _in_range(ej, desde, hasta),
        "entra_auditoria_coalesce": _in_range(fa, desde, hasta),
        "entra_updated_ruta_item": _in_range(ri_upd, desde, hasta),
        "entra_created_actuacion": _in_range(act_cr, desde, hasta),
        "entra_fecha_actuacion": _in_range(act_f, desde, hasta),
        "entra_updated_iniciador": _in_range(ini_upd, desde, hasta) and ini_cumplido,
        "solo_backlog_ejecutado_en_periodo": (
            not _in_range(fc, desde, hasta) and _in_range(ej, desde, hasta)
        ),
    }


def _count_criterion(rows: list, flag: str) -> tuple[int, int]:
    items = [r for r in rows if r.get(flag)]
    acts = {r["actuacion_id"] for r in items}
    return len(items), len(acts)


def _serialize_row(row, flags: dict[str, bool]) -> dict[str, Any]:
    dom = f"{row.calle or ''} {row.numero or ''}".strip() or None
    ej = row.ejecutado_at
    return {
        "ruta_item_id": row.ruta_item_id,
        "ruta_trabajo_id": row.ruta_trabajo_id,
        "ruta_fecha": row.ruta_fecha.isoformat() if row.ruta_fecha else None,
        "ruta_estado": str(row.estado_ruta),
        "estado_ruta_item": str(row.estado_ruta_item),
        "estado_ejecucion": str(row.estado_ejecucion),
        "ejecutado_at": ej.isoformat() if ej else None,
        "ri_created_at": row.ri_created_at.isoformat() if row.ri_created_at else None,
        "ri_updated_at": row.ri_updated_at.isoformat() if row.ri_updated_at else None,
        "actuacion_id": row.actuacion_id,
        "act_fecha": row.act_fecha.isoformat() if row.act_fecha else None,
        "act_created_at": row.act_created_at.isoformat() if row.act_created_at else None,
        "act_tipo": str(row.act_tipo) if row.act_tipo else None,
        "contraproducencia": str(row.contraproducencia) if row.contraproducencia else None,
        "iniciador_id": row.iniciador_id,
        "tipo_iniciador": str(row.tipo_iniciador),
        "estado_iniciador": str(row.estado_iniciador),
        "ini_created_at": row.ini_created_at.isoformat() if row.ini_created_at else None,
        "ini_updated_at": row.ini_updated_at.isoformat() if row.ini_updated_at else None,
        "domicilio": dom,
        "rubro": str(row.rubro_nombre) if row.rubro_nombre else None,
        "fecha_ruta_periodo": (
            row.fecha_ruta_periodo.isoformat() if row.fecha_ruta_periodo else None
        ),
        "fecha_cierre_auditoria": (
            row.fecha_cierre_auditoria.isoformat() if row.fecha_cierre_auditoria else None
        ),
        **flags,
        "deberia_contar_periodo_ruta": flags["entra_criterio_periodo_ruta"],
    }


def _audit_ejecutado_at() -> dict:
    total_real = (
        db.session.query(func.count(RutaItem.id))
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaItem.actuacion_id.isnot(None),
        )
        .scalar()
        or 0
    )
    con_ej = (
        db.session.query(func.count(RutaItem.id))
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaItem.actuacion_id.isnot(None),
            RutaItem.ejecutado_at.isnot(None),
        )
        .scalar()
        or 0
    )
    sin_ej = int(total_real) - int(con_ej)
    pct = round(100.0 * sin_ej / total_real, 1) if total_real else 0.0
    ejemplos_sin = (
        db.session.query(
            RutaItem.id,
            RutaTrabajo.fecha,
            RutaItem.estado_ruta_item,
            RutaItem.estado_ejecucion,
            RutaItem.updated_at,
        )
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaItem.ejecutado_at.is_(None),
        )
        .order_by(RutaItem.updated_at.desc())
        .limit(10)
        .all()
    )
    return {
        "total_realizados_global": int(total_real),
        "con_ejecutado_at": int(con_ej),
        "sin_ejecutado_at": sin_ej,
        "pct_sin_ejecutado_at": pct,
        "ejemplos_recientes_sin_ejecutado_at": [
            {
                "ruta_item_id": rid,
                "ruta_fecha": f.isoformat() if f else None,
                "estado_ruta_item": str(eri),
                "estado_ejecucion": str(ee),
                "updated_at": u.isoformat() if u else None,
            }
            for rid, f, eri, ee, u in ejemplos_sin
        ],
    }


def _actuaciones_usuario_tabla(desde: date, hasta: date) -> list[dict]:
    out: list[dict] = []
    for aid in _ACTUACIONES_USUARIO:
        act = Actuaciones.query.get(aid)
        if act is None:
            out.append({"actuacion_id": aid, "existe": False})
            continue
        items = (
            RutaItem.query.filter(
                RutaItem.actuacion_id == aid,
                RutaItem.deleted_at.is_(None),
            )
            .all()
        )
        item = items[0] if items else None
        ini_estado = None
        cuenta_actual = False
        entra_ej = False
        ruta_fecha = None
        if item:
            ruta = RutaTrabajo.query.get(item.ruta_trabajo_id)
            ini = IniciadorRuta.query.get(item.iniciador_ruta_id)
            ini_estado = str(ini.estado_iniciador) if ini else None
            ruta_fecha = ruta.fecha.isoformat() if ruta and ruta.fecha else None
            if (
                ruta
                and ruta.estado_ruta == "PUBLICADA"
                and item.estado_ruta_item == "FINALIZADO"
                and item.estado_ejecucion == "REALIZADO"
            ):
                cuenta_actual = _in_range(ruta.fecha, desde, hasta)
                if item.ejecutado_at:
                    entra_ej = _in_range(item.ejecutado_at.date(), desde, hasta)
        out.append(
            {
                "actuacion_id": aid,
                "existe": True,
                "fecha": act.fecha.isoformat() if act.fecha else None,
                "created_at": act.created_at.isoformat() if act.created_at else None,
                "tipo": str(act.tipo) if act.tipo else None,
                "contraproducencia": str(act.contraproducencia) if act.contraproducencia else None,
                "ruta_item_id": item.id if item else None,
                "ruta_fecha": ruta_fecha,
                "estado_ruta_item": str(item.estado_ruta_item) if item else None,
                "estado_ejecucion": str(item.estado_ejecucion) if item else None,
                "ejecutado_at": item.ejecutado_at.isoformat() if item and item.ejecutado_at else None,
                "iniciador_estado": ini_estado,
                "cuenta_dashboard_actual": cuenta_actual,
                "entra_ejecutado_at_junio": entra_ej,
                "deberia_contar_estricto": cuenta_actual,
                "nota": (
                    "actuacion sin RutaItem"
                    if not item
                    else (
                        "solo planificada/publicada EN_PROCESO"
                        if item.estado_ruta_item == "EN_PROCESO"
                        else (
                            "cierre REALIZADO; revisar ejecutado_at vs ruta.fecha"
                            if item.estado_ejecucion == "REALIZADO"
                            else "cierre no REALIZADO"
                        )
                    )
                ),
            }
        )
    return out


def run(desde: date, hasta: date) -> dict:
    raw_rows = _base_realizados_q().all()
    serialized: list[dict] = []
    for row in raw_rows:
        flags = _row_flags(row, desde, hasta)
        serialized.append(_serialize_row(row, flags))

    criterios = {
        "A_periodo_ruta_dashboard": {
            "descripcion": "RutaTrabajo.fecha en rango + REALIZADO (Dashboard a4)",
            "flag": "entra_criterio_periodo_ruta",
        },
        "A_legacy_ejecutado_at": {
            "descripcion": "date(ejecutado_at) en rango (criterio anterior)",
            "flag": "entra_ejecutado_at",
        },
        "A_legacy_auditoria_coalesce": {
            "descripcion": "coalesce(ejecutado_at, ruta.fecha) en rango (auditoría)",
            "flag": "entra_auditoria_coalesce",
        },
        "C_updated_ruta_item": {
            "descripcion": "date(RutaItem.updated_at) en rango",
            "flag": "entra_updated_ruta_item",
        },
        "D_created_actuacion": {
            "descripcion": "date(Actuaciones.created_at) en rango",
            "flag": "entra_created_actuacion",
        },
        "E_fecha_actuacion": {
            "descripcion": "Actuaciones.fecha en rango",
            "flag": "entra_fecha_actuacion",
        },
        "F_updated_iniciador_cumplido": {
            "descripcion": "Iniciador CUMPLIDO + updated_at en rango",
            "flag": "entra_updated_iniciador",
        },
    }

    tabla_criterios = []
    for key, meta in criterios.items():
        n_ri, n_act = _count_criterion(serialized, meta["flag"])
        obs = ""
        if key == "A_periodo_ruta_dashboard":
            obs = "criterio vigente Dashboard D1d.11fix-a4"
        elif key == "A_legacy_ejecutado_at":
            backlog = sum(1 for r in serialized if r.get("solo_backlog_ejecutado_en_periodo"))
            obs = f"{backlog} backlog: ejecutado en período pero ruta fuera de período"
        elif key == "A_legacy_auditoria_coalesce":
            obs = "solo auditoría; ya no define KPIs operativos"
        elif key == "E_fecha_actuacion":
            obs = "fecha de publicación de ruta, no de completado"
        tabla_criterios.append(
            {
                "criterio": key,
                "descripcion": meta["descripcion"],
                "ruta_items": n_ri,
                "actuaciones_distinct": n_act,
                "observacion": obs,
            }
        )

    candidatos_periodo = [r for r in serialized if r["entra_criterio_periodo_ruta"]]
    backlog_cerrado = [r for r in serialized if r.get("solo_backlog_ejecutado_en_periodo")]

    estado_ini: dict[tuple, int] = defaultdict(int)
    for r in candidatos_periodo:
        estado_ini[(r["estado_iniciador"], r["tipo_iniciador"])] += 1

    en_proceso = (
        db.session.query(func.count(RutaItem.id))
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "EN_PROCESO",
            RutaTrabajo.fecha >= desde,
            RutaTrabajo.fecha <= hasta,
        )
        .scalar()
        or 0
    )
    no_real = int(
        _no_realizadas_base_query(desde, hasta)
        .with_entities(func.count(func.distinct(RutaItem.id)))
        .scalar()
        or 0
    )

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "A_flujo_completar_trabajo": {
            "endpoint": "POST /api/actuaciones/completar-trabajo/cerrar/<ruta_item_id>",
            "servicio": "cerrar_completar_trabajo_por_ruta_item (completar_trabajo_cierre_service.py)",
            "precondicion": "RutaItem EN_PROCESO, ruta PUBLICADA, actuacion_id ya vinculada",
            "actuacion_id_cuando": "Al publicar ruta (ruta_publicar_service), NO al cerrar",
            "actuaciones_fecha_cuando": "Al publicar ruta (= RutaTrabajo.fecha), NO al completar",
            "campos_al_cerrar_REALIZADO": {
                "RutaItem.ejecutado_at": "datetime.utcnow()",
                "RutaItem.ejecutado_por_user_id": "usuario sesión",
                "RutaItem.estado_ruta_item": "FINALIZADO",
                "RutaItem.estado_ejecucion": "REALIZADO",
                "RutaItem.observaciones_ejecucion": "payload",
                "IniciadorRuta.estado_iniciador": "CUMPLIDO",
                "IniciadorRuta.updated_at": "datetime.utcnow()",
                "RutaItem.updated_at": "onupdate DB (no set explícito en servicio)",
            },
            "fecha_completado_canonica_flujo": "RutaItem.ejecutado_at",
        },
        "B_comparativa_criterios": tabla_criterios,
        "J_dashboard_operativo_vs_backlog": {
            "por_fecha_ruta": {
                "realizados": count_cierres_realizados(desde, hasta),
                "no_realizados": no_real,
                "en_proceso": int(en_proceso),
            },
            "por_ejecutado_at_legacy": sum(
                1 for r in serialized if r.get("entra_ejecutado_at")
            ),
            "backlog_cerrado_en_periodo": backlog_cerrado,
        },
        "C_listado_realizados_periodo_ruta": candidatos_periodo,
        "C_backlog_ejecutado_en_periodo": backlog_cerrado,
        "D_ejecutado_at_audit": _audit_ejecutado_at(),
        "E_estado_iniciador_candidatos_actual": [
            {"estado_iniciador": k[0], "tipo_iniciador": k[1], "cantidad": v}
            for k, v in sorted(estado_ini.items(), key=lambda x: -x[1])
        ],
        "F_actuaciones_702_763": _actuaciones_usuario_tabla(desde, hasta),
        "G_posible_bug_estados": {
            "nota": (
                "FINALIZADO+REALIZADO solo se setean en cerrar_completar_trabajo_por_ruta_item "
                "desde EN_PROCESO. actuacion_id se setea al publicar (EN_PROCESO), no implica completado."
            ),
            "nota_dashboard_a4": (
                "Dashboard operativo usa RutaTrabajo.fecha; ejecutado_at queda para auditoría."
            ),
        },
        "H_conclusiones_pendientes": {
            "preguntas": [
                "¿Por qué 14? Ver C_listado y solo_por_fallback",
                "¿Cuántos ejecutado_at en junio? Ver B criterio B",
                "¿Inflación por ruta.fecha? Ver C_solo_por_fallback",
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
