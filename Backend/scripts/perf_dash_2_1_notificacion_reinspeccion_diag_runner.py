"""
PERF-DASH.2.1-DIAG — Notificación histórica recontada en reinspección por notificación.
Uso: cd Backend && set PYTHONPATH=. && python scripts/perf_dash_2_1_notificacion_reinspeccion_diag_runner.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import and_, exists, func

from app import create_app
from app.database import db
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    actuacion_ids_realizadas_subquery,
)
from app.domains.indicadores.services.indicadores_resumen_service import (
    _count_actas_labradas,
    _notificacion_labarda_exists,
)
from app.models import (
    Actuaciones,
    IniciadorRuta,
    Notificacion,
    RutaItem,
    RutaTrabajo,
    notificacion_motivo,
)
from app.models.inspeccion import Inspeccion

OUTPUT = (
    Path(__file__).resolve().parent
    / "output"
    / "perf_dash_2_1_notificacion_reinspeccion_diag_20260922.json"
)

BASELINE_DESDE = date(2026, 9, 1)
BASELINE_HASTA = date(2026, 9, 21)


def _notificacion_labarda_en_actuacion(act_id_col):
    """EXISTS motivos para notificacion_id de la actuación."""
    return exists().where(
        notificacion_motivo.c.notificacion_id == act_id_col,
        notificacion_motivo.c.deleted_at.is_(None),
    )


def _query_reinspeccion_notif_realizadas(desde: date, hasta: date) -> list[dict[str, Any]]:
    """Cierres REINSPECCION_NOTIFICACION realizados en período operativo."""
    rows = (
        db.session.query(
            RutaItem.id.label("ruta_item_id"),
            Actuaciones.id.label("actuacion_reinspeccion_id"),
            Actuaciones.notificacion_id.label("act_notificacion_id"),
            Actuaciones.tipo.label("act_tipo"),
            IniciadorRuta.id.label("iniciador_id"),
            IniciadorRuta.notificacion_id.label("ini_notificacion_id"),
            IniciadorRuta.actuacion_id.label("ini_actuacion_origen_id"),
            RutaTrabajo.fecha.label("ruta_fecha"),
        )
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaItem.actuacion_id.isnot(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha >= desde,
            RutaTrabajo.fecha <= hasta,
        )
        .order_by(RutaItem.id)
        .all()
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        act_nid = int(r.act_notificacion_id) if r.act_notificacion_id else None
        ini_nid = int(r.ini_notificacion_id) if r.ini_notificacion_id else None
        es_vinculo_origen = (
            act_nid is not None and ini_nid is not None and act_nid == ini_nid
        )
        tiene_inspeccion = (
            db.session.query(Inspeccion.id)
            .filter(Inspeccion.actuacion_id == r.actuacion_reinspeccion_id)
            .first()
            is not None
        )
        cuenta_kpi_actual = False
        if act_nid is not None:
            cuenta_kpi_actual = bool(
                db.session.query(Actuaciones.id)
                .filter(
                    Actuaciones.id == r.actuacion_reinspeccion_id,
                    Actuaciones.notificacion_id.isnot(None),
                    _notificacion_labarda_exists(),
                )
                .first()
            )
        origen_act_nid = None
        if r.ini_actuacion_origen_id:
            origen = db.session.get(Actuaciones, int(r.ini_actuacion_origen_id))
            if origen:
                origen_act_nid = origen.notificacion_id
        out.append(
            {
                "ruta_item_id": int(r.ruta_item_id),
                "actuacion_reinspeccion_id": int(r.actuacion_reinspeccion_id),
                "iniciador_id": int(r.iniciador_id),
                "ruta_fecha": r.ruta_fecha.isoformat(),
                "act_tipo": r.act_tipo,
                "act_notificacion_id": act_nid,
                "ini_notificacion_id": ini_nid,
                "ini_actuacion_origen_id": int(r.ini_actuacion_origen_id)
                if r.ini_actuacion_origen_id
                else None,
                "origen_actuacion_notificacion_id": int(origen_act_nid)
                if origen_act_nid
                else None,
                "vinculo_notificacion_origen_en_acta": es_vinculo_origen,
                "tiene_inspeccion_visita": tiene_inspeccion,
                "cuenta_en_kpi_notificacion_actual": cuenta_kpi_actual,
                "falso_positivo_kpi": es_vinculo_origen and cuenta_kpi_actual,
            }
        )
    return out


def _query_notificaciones_por_actuacion_realizada(desde: date, hasta: date) -> list[dict[str, Any]]:
    """Actuaciones realizadas en período que pasan filtro KPI notificación actual."""
    sq = actuacion_ids_realizadas_subquery(desde, hasta)
    rows = (
        db.session.query(
            Actuaciones.id,
            Actuaciones.notificacion_id,
            Actuaciones.tipo,
            Actuaciones.fecha,
            Actuaciones.anio,
            Actuaciones.mes,
        )
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Actuaciones.notificacion_id.isnot(None),
            _notificacion_labarda_exists(),
        )
        .all()
    )
    result: list[dict[str, Any]] = []
    for act_id, nid, tipo, fecha, anio, mes in rows:
        ini = (
            db.session.query(IniciadorRuta)
            .join(RutaItem, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
            .filter(
                RutaItem.actuacion_id == act_id,
                RutaItem.deleted_at.is_(None),
                IniciadorRuta.deleted_at.is_(None),
            )
            .order_by(RutaItem.id.desc())
            .first()
        )
        es_reinsp = ini is not None and ini.tipo_iniciador == "REINSPECCION_NOTIFICACION"
        es_origen = (
            es_reinsp
            and ini.notificacion_id is not None
            and int(ini.notificacion_id) == int(nid)
        )
        noti = db.session.get(Notificacion, int(nid)) if nid else None
        otras_acts_misma_noti = (
            db.session.query(func.count(Actuaciones.id))
            .filter(Actuaciones.notificacion_id == nid)
            .scalar()
            if nid
            else 0
        )
        result.append(
            {
                "actuacion_id": int(act_id),
                "notificacion_id": int(nid) if nid else None,
                "actuacion_tipo": tipo,
                "actuacion_fecha": fecha.isoformat() if fecha else None,
                "notificacion_mes_anio": f"{mes}/{anio}" if noti else None,
                "iniciador_tipo": ini.tipo_iniciador if ini else None,
                "iniciador_id": int(ini.id) if ini else None,
                "es_reinspeccion_notificacion": es_reinsp,
                "notificacion_es_origen_del_iniciador": es_origen,
                "actuaciones_con_misma_notificacion_id": int(otras_acts_misma_noti or 0),
                "clasificacion": (
                    "B_reconteo_origen_reinspeccion"
                    if es_origen
                    else "A_acta_labrada_en_esta_actuacion"
                ),
            }
        )
    return result


def _find_best_reproduction_case(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    for c in cases:
        if c.get("falso_positivo_kpi"):
            return c
    return cases[0] if cases else None


def main() -> None:
    app = create_app()
    with app.app_context():
        ejecutivo = build_indicadores_ejecutivo(BASELINE_DESDE, BASELINE_HASTA)
        sq = actuacion_ids_realizadas_subquery(BASELINE_DESDE, BASELINE_HASTA)
        actas = _count_actas_labradas(sq)

        reinsp_cases = _query_reinspeccion_notif_realizadas(BASELINE_DESDE, BASELINE_HASTA)
        notif_breakdown = _query_notificaciones_por_actuacion_realizada(
            BASELINE_DESDE, BASELINE_HASTA
        )

        false_positives = [r for r in notif_breakdown if r["clasificacion"] == "B_reconteo_origen_reinspeccion"]
        true_labradas = [r for r in notif_breakdown if r["clasificacion"] == "A_acta_labrada_en_esta_actuacion"]
        reconteos_unicos_noti = len({r["notificacion_id"] for r in false_positives})
        current_notif_count = actas.notificacion
        corrected_notif_count = len(true_labradas)

        # Caso cross-month: reinspección en período con noti origen fuera
        cross_month: list[dict[str, Any]] = []
        for fp in false_positives:
            act = db.session.get(Actuaciones, fp["actuacion_id"])
            noti = db.session.get(Notificacion, fp["notificacion_id"])
            if act and noti and (act.mes != noti.mes or act.anio != noti.anio):
                cross_month.append(
                    {
                        "actuacion_reinspeccion_id": fp["actuacion_id"],
                        "notificacion_id": fp["notificacion_id"],
                        "reinspeccion_periodo": f"{act.mes}/{act.anio}",
                        "notificacion_labrada_periodo": f"{noti.mes}/{noti.anio}",
                    }
                )

        reproduction = _find_best_reproduction_case(reinsp_cases)
        if reproduction and reproduction.get("ini_actuacion_origen_id"):
            origen = db.session.get(Actuaciones, reproduction["ini_actuacion_origen_id"])
            if origen:
                reproduction["actuacion_inicial_id"] = int(origen.id)
                reproduction["notificacion_origen_id"] = reproduction.get("ini_notificacion_id")

        # Auditoría otros tipos: inspección usa tabla hija; comprobación excluye PENDIENTE
        otros_tipos = {
            "inspeccion": {
                "count_path": "COUNT(inspeccion.id) JOIN actuacion_id",
                "riesgo_referencia_origen": "bajo — acta propia en tabla hija",
            },
            "comprobacion": {
                "count_path": "COUNT(actuaciones) WHERE comprobacion_id + motivo != PENDIENTE",
                "riesgo_referencia_origen": "medio — previas_service asigna comprobacion_id referencial; filtro PENDIENTE mitiga previas documentales",
            },
            "clausura": {
                "count_path": "COUNT(clausura.id) JOIN actuacion_id",
                "riesgo_referencia_origen": "bajo — acta propia en tabla hija",
            },
            "decomiso": {
                "count_path": "COUNT(decomiso.id) JOIN actuacion_id",
                "riesgo_referencia_origen": "bajo — acta propia en tabla hija",
            },
            "notificacion": {
                "count_path": "COUNT(actuaciones) WHERE notificacion_id + EXISTS(notificacion_motivo)",
                "riesgo_referencia_origen": "alto — FK referencial de origen copiada en reinspección (_vincular_notificacion_reinspeccion_en_acta)",
            },
        }

        report = {
            "ticket": "PERF-DASH.2.1-DIAG",
            "date": "2026-09-22",
            "writes_executed": False,
            "periodo_analizado": {
                "desde": BASELINE_DESDE.isoformat(),
                "hasta": BASELINE_HASTA.isoformat(),
            },
            "reproduction_case": reproduction,
            "reinspeccion_notificacion_realizadas_en_periodo": reinsp_cases,
            "notificacion_kpi_breakdown": notif_breakdown,
            "current_query_path": {
                "function": "_count_actas_labradas",
                "file": "app/domains/indicadores/services/indicadores_resumen_service.py",
                "notificacion_logic": (
                    "Subquery realizadas (ruta_item REALIZADO en período) "
                    "→ COUNT(DISTINCT actuaciones.id) WHERE actuaciones.notificacion_id IS NOT NULL "
                    "AND EXISTS(notificacion_motivo para ese notificacion_id)"
                ),
                "universo": "actuacion_ids_realizadas_subquery (cierre operativo por RutaTrabajo.fecha)",
            },
            "wrong_relation_path": {
                "description": (
                    "Al completar REINSPECCION_NOTIFICACION, "
                    "_vincular_notificacion_reinspeccion_en_acta copia iniciador.notificacion_id "
                    "(notificación histórica de origen) a act.notificacion_id de la actuación de reinspección"
                ),
                "workflow_file": "app/domains/actuaciones/services/completar_trabajo_cierre_service.py",
                "workflow_function": "_vincular_notificacion_reinspeccion_en_acta",
                "purpose_in_workflow": (
                    "Permite list_reinspeccion_notificacion_operativas detectar reinspección vía subq_reinsp"
                ),
                "kpi_side_effect": (
                    "La actuación de reinspección entra al subquery realizadas y cumple "
                    "notificacion_id + motivos de la notificación ORIGEN → +1 falso en KPI notificación"
                ),
                "domain_awareness_exists": {
                    "function": "notificacion_es_origen_reinspeccion_notificacion_en_actuacion",
                    "file": "app/domains/actuaciones/services/oficio_circuito_service.py",
                    "used_in_kpi": False,
                },
            },
            "canonical_relation_path": {
                "invariante": "Contar notificación solo si fue labrada en ESA actuación",
                "opciones": [
                    "Excluir actuaciones REINSPECCION_NOTIFICACION donde act.notificacion_id == iniciador.notificacion_id (origen referencial)",
                    "Contar por notificacion creada/vinculada en la visita (attach_notificacion) no por FK referencial de circuito",
                    "Usar notificacion_es_origen_reinspeccion_notificacion_en_actuacion en filtro SQL del KPI",
                ],
                "reinspeccion_kpi_separado": (
                    "reinspecciones_notificacion_realizadas usa visitas_realizadas_por_tipo_iniciador "
                    "(tipo iniciador REINSPECCION_NOTIFICACION) — correcto y separado"
                ),
            },
            "root_cause": (
                "Desacople entre semántica operativa (FK referencial para trazabilidad de circuito) "
                "y semántica del KPI (acta labrada en la visita). "
                "_count_actas_labradas trata cualquier actuaciones.notificacion_id con motivos como acta labrada, "
                "sin excluir la notificación de origen copiada en reinspecciones sin nueva notificación."
            ),
            "affected_kpis": [
                "ejecutivo.actas_por_tipo.notificacion",
                "ejecutivo.kpis.actas_labradas (suma total)",
                "productividad.actas_por_inspector.notificacion",
                "riesgo.top_motivos_notificacion (si la actuación reinspección arrastra notificacion_id origen)",
            ],
            "not_affected_kpis": [
                "reinspecciones_notificacion_realizadas (tipo iniciador)",
                "inspeccion/clausura/decomiso actas (tablas hijas por actuacion_id)",
            ],
            "baseline_previous": {
                "actas_labradas_total": ejecutivo.kpis.actas_labradas,
                "notificacion": current_notif_count,
                "source": "Medición sandbox actual 2026-09-01..2026-09-21",
            },
            "perf_dash_2_frozen_baseline": {
                "notificacion": 10,
                "actas_labradas_total": 35,
                "note": (
                    "Congelado en PERF-DASH.2; puede diferir por drift de sandbox. "
                    "Con la misma lógica de reconteo, valor corregido estimado: notificacion=8, total=33."
                ),
                "corrected_estimate": {
                    "notificacion": max(0, 10 - len(false_positives)),
                    "actas_labradas_total": 35 - (current_notif_count - corrected_notif_count),
                },
            },
            "baseline_corrected_expected": {
                "notificacion": corrected_notif_count,
                "notificacion_reconteos_por_reinspeccion": len(false_positives),
                "notificaciones_origen_distintas_recontadas": reconteos_unicos_noti,
                "actas_labradas_total": (
                    ejecutivo.kpis.actas_labradas
                    - (current_notif_count - corrected_notif_count)
                ),
                "delta_notificacion": current_notif_count - corrected_notif_count,
                "clasificacion_A_actas_reales": len(true_labradas),
                "clasificacion_B_reconteos": len(false_positives),
            },
            "cross_month_false_positives": cross_month,
            "otros_tipos_acta_audit": otros_tipos,
            "test_matrix": {
                "A": {
                    "descripcion": "Inspección inicial con notificación labrada",
                    "expected": "notificacion +1 en actuación A",
                },
                "B": {
                    "descripcion": "Reinspección por notificación sin nueva notificación",
                    "expected": "reinspeccion_notificacion +1; notificacion +0 adicional",
                    "bug_actual": "notificacion +1 adicional si act.notificacion_id = ini.notificacion_id",
                },
                "C": {
                    "descripcion": "Reinspección con nueva notificación (attach)",
                    "expected": "reinspeccion +1; notificacion +1 solo por acta nueva",
                },
                "D": {
                    "descripcion": "Origen agosto, reinspección septiembre",
                    "expected": "septiembre: reinspeccion +1, notificacion +0",
                    "casos_encontrados": len(cross_month),
                },
                "E": {
                    "descripcion": "Origen y reinspección mismo mes",
                    "expected": "notificacion mensual = 1 (no 2)",
                },
            },
            "recommended_fix": {
                "scope": "Solo filtro notificación en _count_actas_labradas (y queries paralelas: productividad actas, top motivos si aplica)",
                "approach": (
                    "En SQL: excluir actuaciones realizadas cuyo par (actuacion_id, notificacion_id) "
                    "sea vínculo referencial REINSPECCION_NOTIFICACION "
                    "(act.notificacion_id = iniciador.notificacion_id del cierre). "
                    "Reutilizar semántica de notificacion_es_origen_reinspeccion_notificacion_en_actuacion."
                ),
                "preserve_performance": (
                    "Mantener 1 SELECT agregado; agregar NOT EXISTS / LEFT JOIN anti-pattern "
                    "sobre iniciador_ruta+ruta_item del mismo cierre, no volver a 5 COUNTs."
                ),
                "do_not_change": [
                    "workflow completar_trabajo / _vincular_notificacion_reinspeccion_en_acta",
                    "KPI reinspecciones_notificacion_realizadas",
                ],
            },
            "status": "DIAG_COMPLETE",
        }

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {OUTPUT} (status={report['status']})")
        print(
            f"notificacion KPI: {current_notif_count} actual -> {corrected_notif_count} corrected "
            f"({len(false_positives)} reconteos)"
        )


if __name__ == "__main__":
    main()
