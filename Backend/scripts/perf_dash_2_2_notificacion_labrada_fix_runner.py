"""
PERF-DASH.2.2 — Verificación post-fix notificación labrada vs origen.
Uso: cd Backend && set PYTHONPATH=. && python scripts/perf_dash_2_2_notificacion_labrada_fix_runner.py
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from sqlalchemy import event

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
)
from app.models import Actuaciones, IniciadorRuta, RutaItem

OUTPUT = (
    Path(__file__).resolve().parent
    / "output"
    / "perf_dash_2_2_notificacion_labrada_fix_20260922.json"
)

DESDE = date(2026, 9, 1)
HASTA = date(2026, 9, 21)

SANDBOX_CASES = (10590, 11420)


class QueryCounter:
    def __init__(self) -> None:
        self.count = 0

    def attach(self) -> None:
        @event.listens_for(db.engine, "after_cursor_execute")
        def after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            self.count += 1


def _case_detail(act_id: int) -> dict:
    act = db.session.get(Actuaciones, act_id)
    if act is None:
        return {"actuacion_id": act_id, "found": False}
    item = (
        RutaItem.query.filter_by(actuacion_id=act_id, deleted_at=None)
        .order_by(RutaItem.id.desc())
        .first()
    )
    ini = (
        db.session.get(IniciadorRuta, item.iniciador_ruta_id) if item else None
    )
    return {
        "actuacion_id": act_id,
        "found": True,
        "notificacion_id": act.notificacion_id,
        "iniciador_id": ini.id if ini else None,
        "iniciador_notificacion_id": ini.notificacion_id if ini else None,
        "es_vinculo_origen": bool(
            ini
            and ini.tipo_iniciador == "REINSPECCION_NOTIFICACION"
            and ini.notificacion_id is not None
            and act.notificacion_id is not None
            and int(ini.notificacion_id) == int(act.notificacion_id)
        ),
    }


def main() -> None:
    app = create_app()
    with app.app_context():
        qc = QueryCounter()
        qc.attach()
        t0 = time.perf_counter()
        ej = build_indicadores_ejecutivo(DESDE, HASTA)
        ms = round((time.perf_counter() - t0) * 1000, 1)

        sq = actuacion_ids_realizadas_subquery(DESDE, HASTA)
        qc2 = QueryCounter()
        qc2.attach()
        actas = _count_actas_labradas(sq)

        report = {
            "ticket": "PERF-DASH.2.2",
            "date": "2026-09-22",
            "writes_executed": False,
            "migration_required": False,
            "implementation_strategy": (
                "NOT EXISTS sobre ruta_item+iniciador_ruta REINSPECCION_NOTIFICACION "
                "cuando act.notificacion_id == iniciador.notificacion_id; "
                "integrado en _notificacion_labrada_kpi_filter dentro del SELECT agregado único."
            ),
            "canonical_origin_rule": (
                "notificacion_es_origen_reinspeccion_notificacion_en_actuacion "
                "(oficio_circuito_service.py) — expresión SQL en notificacion_labrada_kpi_filters.py"
            ),
            "query_before": (
                "COUNT actuaciones realizadas WHERE notificacion_id IS NOT NULL "
                "AND EXISTS(notificacion_motivo)"
            ),
            "query_after": (
                "COUNT actuaciones realizadas WHERE notificacion_id IS NOT NULL "
                "AND EXISTS(notificacion_motivo) "
                "AND NOT EXISTS(reinspeccion origen referencial)"
            ),
            "sandbox_cases": {
                "actuacion_10590": _case_detail(10590),
                "actuacion_11420": _case_detail(11420),
            },
            "before": {
                "notificacion": 11,
                "total_actas": 38,
                "source": "PERF-DASH.2.1 diag pre-fix",
            },
            "after": {
                "notificacion": ej.actas_por_tipo.notificacion,
                "total_actas": ej.kpis.actas_labradas,
                "actas_por_tipo": ej.actas_por_tipo.model_dump(),
            },
            "reinspecciones_notificacion_before": 1,
            "reinspecciones_notificacion_after": ej.kpis.reinspecciones_notificacion_realizadas,
            "other_kpis_equal": {
                "actuaciones_realizadas": ej.kpis.actuaciones_realizadas,
                "inspecciones_realizadas": ej.kpis.inspecciones_realizadas,
                "reinspecciones_oficio_realizadas": ej.kpis.reinspecciones_oficio_realizadas,
                "mercaderia_decomisada_kg": ej.kpis.mercaderia_decomisada_kg,
            },
            "productividad_audit": "query_actas_por_inspector usa _notificacion_labrada_kpi_filter",
            "riesgo_audit": "query_top_motivos_notificacion excluye origen referencial",
            "pdf_export_audit": "Panel/PDF consumen ejecutivo API — sin recálculo separado",
            "performance": {
                "endpoint_ms_after": ms,
                "query_count_ejecutivo_after": qc.count,
                "query_count_actas_subquery_after": qc2.count,
                "note": "Mantiene SELECT agregado único; sin regresión a 5 COUNTs",
            },
            "tests": {
                "initial": "test_a_inicial_labra_notificacion_cuenta",
                "rein_without_new_notification": "test_b_reinspeccion_sin_nueva_notificacion_no_recuenta",
                "rein_with_new_notification": "test_c_reinspeccion_con_nueva_notificacion_cuenta_solo_nueva",
                "cross_month": "test_d_cross_month_reinspeccion_no_arrastra_notif",
                "same_month": "test_e_mismo_mes_notificacion_cuenta_una_sola_vez",
                "normal_notification": "test_f_actuacion_normal_con_notificacion_sigue_contando",
                "retry": "test_g_dos_reinspecciones_misma_notificacion_origen_no_recuentan",
            },
            "status": (
                "PASS"
                if ej.actas_por_tipo.notificacion == 9 and ej.kpis.actas_labradas == 36
                else "FAIL"
            ),
        }

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {OUTPUT}")
        print(f"status={report['status']} notif={ej.actas_por_tipo.notificacion} total={ej.kpis.actas_labradas}")


if __name__ == "__main__":
    main()
