"""
D1d.11fix-a2 — Diagnóstico DB real: oficio, ratificaciones, verificar e informar, rubros.

Uso:
    cd Backend && python scripts/diagnostico_indicadores_a2.py
    python scripts/diagnostico_indicadores_a2.py --desde 2025-01-01 --hasta 2026-12-31
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, or_, text

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_operativos_queries import (
    _fecha_cierre_ruta_expr,
)
from app.models import (
    Actuaciones,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Oficio,
    Rubro,
    RutaItem,
    RutaTrabajo,
)


def _norm(s: str | None) -> str:
    if not s:
        return ""
    return " ".join(str(s).upper().replace("_", " ").split())


def _match_subtipo(tipo: str | None) -> str | None:
    n = _norm(tipo)
    if not n:
        return None
    if "RATIFICACION" in n and "CLAUSURA" in n:
        return "RATIFICACION_CLAUSURA"
    if "RATIFICACION" in n and "DECOMISO" in n:
        return "RATIFICACION_DECOMISO"
    if "VERIFICAR" in n and "INFORMAR" in n:
        return "VERIFICAR_INFORMAR"
    if n == "REINSPECCION":
        return "REINSPECCION_GENERICO"
    return None


def base_realizados_q(desde: date, hasta: date):
    fecha_cierre = _fecha_cierre_ruta_expr()
    return (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            RutaTrabajo.fecha.label("ruta_fecha"),
            func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha).label("fecha_cierre"),
            Actuaciones.id.label("actuacion_id"),
            Actuaciones.fecha.label("actuacion_fecha"),
            Actuaciones.tipo.label("actuacion_tipo"),
            Actuaciones.domicilio_id.label("act_domicilio_id"),
            Actuaciones.establecimiento_operativo_id.label("act_establecimiento_id"),
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.tipo_iniciador.label("tipo_iniciador"),
            IniciadorRuta.estado_iniciador.label("estado_iniciador"),
            IniciadorRuta.domicilio_id.label("ini_domicilio_id"),
            IniciadorRuta.oficio_id.label("oficio_id"),
            IniciadorRuta.comprobacion_id.label("comprobacion_id"),
            Oficio.causa.label("oficio_causa"),
            Oficio.numero_oficio.label("oficio_numero"),
            Domicilio.rubro_id.label("act_rubro_id"),
            Rubro.nombre.label("act_rubro_nombre"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .outerjoin(Oficio, IniciadorRuta.oficio_id == Oficio.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
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


def run(desde: date, hasta: date) -> dict:
    rows = base_realizados_q(desde, hasta).all()

    # A. tipos iniciador
    ini_total: dict[str, int] = defaultdict(int)
    ini_realizado: dict[str, int] = defaultdict(int)
    for r in rows:
        ini_realizado[str(r.tipo_iniciador)] += 1

    all_ini = (
        db.session.query(IniciadorRuta.tipo_iniciador, func.count(IniciadorRuta.id))
        .filter(IniciadorRuta.deleted_at.is_(None))
        .group_by(IniciadorRuta.tipo_iniciador)
        .all()
    )
    for tipo, cnt in all_ini:
        ini_total[str(tipo)] = int(cnt)

    # B. tipos actuación
    act_tipo_all: dict[str, int] = defaultdict(int)
    act_tipo_realizado: dict[str, int] = defaultdict(int)
    act_tipo_en_reins_oficio: dict[str, int] = defaultdict(int)

    for r in rows:
        t = str(r.actuacion_tipo) if r.actuacion_tipo else "(null)"
        act_tipo_realizado[t] += 1
        if str(r.tipo_iniciador) == "REINSPECCION_OFICIO":
            act_tipo_en_reins_oficio[t] += 1

    act_all = (
        db.session.query(Actuaciones.tipo, func.count(Actuaciones.id))
        .group_by(Actuaciones.tipo)
        .all()
    )
    for tipo, cnt in act_all:
        act_tipo_all[str(tipo) if tipo else "(null)"] = int(cnt)

    # C. ratificaciones / verificar — cruce iniciador × actuacion.tipo
    cruce_oficio: dict[str, int] = defaultdict(int)
    muestras_subtipo: list[dict] = []

    for r in rows:
        sub_ini = _match_subtipo(str(r.tipo_iniciador))
        sub_act = _match_subtipo(str(r.actuacion_tipo))
        key = f"ini={r.tipo_iniciador}|act={r.actuacion_tipo or 'null'}"
        cruce_oficio[key] += 1

        if str(r.tipo_iniciador) == "REINSPECCION_OFICIO" and sub_act:
            if len(muestras_subtipo) < 15:
                exp = None
                if r.oficio_id:
                    exp = (
                        Expediente.query.filter(
                            Expediente.oficio_id == r.oficio_id,
                            Expediente.deleted_at.is_(None),
                        )
                        .order_by(Expediente.id.desc())
                        .first()
                    )
                muestras_subtipo.append(
                    {
                        "ruta_item_id": r.ruta_item_id,
                        "fecha_cierre": str(r.fecha_cierre),
                        "actuacion_id": r.actuacion_id,
                        "actuacion_tipo": r.actuacion_tipo,
                        "tipo_iniciador": r.tipo_iniciador,
                        "oficio_id": r.oficio_id,
                        "oficio_causa": r.oficio_causa,
                        "oficio_numero": r.oficio_numero,
                        "expediente_tipo": getattr(exp, "tipo_expediente", None) if exp else None,
                        "expediente_numero": getattr(exp, "numero_expediente", None) if exp else None,
                        "act_domicilio_id": r.act_domicilio_id,
                        "ini_domicilio_id": r.ini_domicilio_id,
                        "act_rubro": r.act_rubro_nombre,
                    }
                )

    # KPI actual vs propuesto
    kpi_actual = {
        "RATIFICACION_CLAUSURA_OFICIO": sum(
            1 for r in rows if str(r.tipo_iniciador) == "RATIFICACION_CLAUSURA_OFICIO"
        ),
        "RATIFICACION_DECOMISO_OFICIO": sum(
            1 for r in rows if str(r.tipo_iniciador) == "RATIFICACION_DECOMISO_OFICIO"
        ),
        "VERIFICAR_INFORMAR_OFICIO": sum(
            1 for r in rows if str(r.tipo_iniciador) == "VERIFICAR_INFORMAR_OFICIO"
        ),
        "REINSPECCION_OFICIO": sum(1 for r in rows if str(r.tipo_iniciador) == "REINSPECCION_OFICIO"),
    }
    kpi_propuesto = {
        "ratificacion_clausura": sum(
            1
            for r in rows
            if _match_subtipo(str(r.actuacion_tipo)) == "RATIFICACION_CLAUSURA"
            or str(r.tipo_iniciador) == "RATIFICACION_CLAUSURA_OFICIO"
        ),
        "ratificacion_decomiso": sum(
            1
            for r in rows
            if _match_subtipo(str(r.actuacion_tipo)) == "RATIFICACION_DECOMISO"
            or str(r.tipo_iniciador) == "RATIFICACION_DECOMISO_OFICIO"
        ),
        "verificar_informar": sum(
            1
            for r in rows
            if _match_subtipo(str(r.actuacion_tipo)) == "VERIFICAR_INFORMAR"
            or str(r.tipo_iniciador) == "VERIFICAR_INFORMAR_OFICIO"
        ),
        "reinspeccion_oficio_solo_generico": sum(
            1
            for r in rows
            if str(r.tipo_iniciador) == "REINSPECCION_OFICIO"
            and _match_subtipo(str(r.actuacion_tipo)) not in (
                "RATIFICACION_CLAUSURA",
                "RATIFICACION_DECOMISO",
                "VERIFICAR_INFORMAR",
            )
        ),
    }

    # D. rubros
    total_cierres = len(rows)
    con_act = total_cierres
    con_act_dom = sum(1 for r in rows if r.act_domicilio_id)
    con_ini_dom = sum(1 for r in rows if r.ini_domicilio_id)
    con_rubro_act = sum(1 for r in rows if r.act_rubro_id)
    sin_rubro_act = sum(1 for r in rows if r.act_domicilio_id and not r.act_rubro_id)
    sin_dom_act_con_ini = sum(
        1 for r in rows if not r.act_domicilio_id and r.ini_domicilio_id
    )

    # rubro vía iniciador.domicilio
    rubro_via_ini = 0
    rubro_via_ini_nombres: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.act_rubro_id:
            continue
        if not r.ini_domicilio_id:
            continue
        dom_ini = db.session.get(Domicilio, r.ini_domicilio_id)
        if dom_ini and dom_ini.rubro_id:
            rubro_via_ini += 1
            rub = db.session.get(Rubro, dom_ini.rubro_id)
            if rub:
                rubro_via_ini_nombres[rub.nombre] += 1

    rubro_top_actual = defaultdict(int)
    for r in rows:
        if r.act_rubro_nombre:
            rubro_top_actual[r.act_rubro_nombre] += 1

    # Textos relacionados en oficio.causa
    oficio_causas = (
        db.session.query(Oficio.causa, func.count(Oficio.id))
        .filter(
            Oficio.deleted_at.is_(None),
            or_(
                Oficio.causa.ilike("%ratif%"),
                Oficio.causa.ilike("%decomiso%"),
                Oficio.causa.ilike("%clausura%"),
                Oficio.causa.ilike("%verificar%"),
                Oficio.causa.ilike("%informar%"),
            ),
        )
        .group_by(Oficio.causa)
        .limit(20)
        .all()
    )

    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "cierres_realizados_total": total_cierres,
        "A_tipos_iniciador": {
            "total_en_bd": dict(sorted(ini_total.items())),
            "con_cierre_realizado": dict(sorted(ini_realizado.items())),
        },
        "B_tipos_actuacion": {
            "total_en_bd": dict(sorted(act_tipo_all.items(), key=lambda x: -x[1])[:30]),
            "en_cierres_realizados": dict(sorted(act_tipo_realizado.items(), key=lambda x: -x[1])),
            "en_REINSPECCION_OFICIO_realizado": dict(
                sorted(act_tipo_en_reins_oficio.items(), key=lambda x: -x[1])
            ),
        },
        "C_ratificaciones_verificar": {
            "kpi_dashboard_actual_por_tipo_iniciador": kpi_actual,
            "kpi_propuesto_por_actuacion_tipo_o_iniciador_especifico": kpi_propuesto,
            "cruce_ini_x_act_top": dict(
                sorted(cruce_oficio.items(), key=lambda x: -x[1])[:25]
            ),
            "muestras_REINSPECCION_OFICIO_con_subtipo_act": muestras_subtipo,
            "oficio_causas_relacionadas": [
                {"causa": c, "count": int(n)} for c, n in oficio_causas
            ],
        },
        "D_rubros": {
            "con_actuacion": con_act,
            "con_act_domicilio": con_act_dom,
            "con_ini_domicilio": con_ini_dom,
            "con_rubro_via_act_domicilio": con_rubro_act,
            "sin_rubro_con_act_domicilio": sin_rubro_act,
            "sin_act_domicilio_pero_ini_tiene_domicilio": sin_dom_act_con_ini,
            "recuperables_rubro_via_ini_domicilio": rubro_via_ini,
            "top_rubros_join_actual_act_domicilio": dict(
                sorted(rubro_top_actual.items(), key=lambda x: -x[1])[:15]
            ),
            "top_rubros_si_usara_ini_domicilio": dict(
                sorted(rubro_via_ini_nombres.items(), key=lambda x: -x[1])[:15]
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default="2025-01-01")
    parser.add_argument("--hasta", default="2026-12-31")
    args = parser.parse_args()
    desde = date.fromisoformat(args.desde)
    hasta = date.fromisoformat(args.hasta)

    app = create_app()
    with app.app_context():
        out = run(desde, hasta)
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
