"""GESTIÓN-PERF.1-C — diagnóstico Comprobaciones (solo lectura)."""
from __future__ import annotations

import time

from app import create_app
from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_pendiente_expediente_row,
    actuacion_to_pendiente_oficio_row,
)
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_resumen_row,
    reinspeccion_oficio_bandeja_row,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_comprobacion_recorrido,
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from sqlalchemy import text


def _timed(label: str, fn):
    t0 = time.perf_counter()
    out = fn()
    ms = (time.perf_counter() - t0) * 1000
    n = len(out) if isinstance(out, list) else out
    print(f"{label}: n={n} ms={ms:.1f}")
    return out, ms


def main() -> None:
    app = create_app({"TESTING": True})
    with app.app_context():
        vol = db.session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM actuaciones WHERE comprobacion_id IS NOT NULL) AS act_con_comp,
                  (SELECT COUNT(DISTINCT comprobacion_id) FROM actuaciones WHERE comprobacion_id IS NOT NULL) AS distinct_comp,
                  (SELECT COUNT(*) FROM comprobacion) AS total_comp
                """
            )
        ).one()
        print(
            f"VOLUMEN actuaciones_con_comprobacion={vol.act_con_comp} "
            f"distinct_comprobacion_id={vol.distinct_comp} total_comprobacion={vol.total_comp}"
        )

        base_op = {
            "source_type": "comprobacion",
            "omitir_rango_fecha": True,
        }

        # CP — Pendientes expediente
        f_exp = ActuacionesPendientesFilters.model_validate(base_op)
        acts, q_ms = _timed("cp_expediente_query", lambda: get_pendientes_expediente(f_exp))
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts)
        rows = [
            actuacion_to_pendiente_expediente_row(
                a, counts_by_eo=counts, expediente_list_channel="comprobacion"
            )
            for a in acts
        ]
        p_ms = (time.perf_counter() - t0) * 1000
        print(
            f"cp_expediente_presenter: rows={len(rows)} ms={p_ms:.1f} "
            f"per_row={p_ms/len(rows) if rows else 0:.2f} total_ms={q_ms+p_ms:.1f}"
        )

        # CP — Pendientes oficio
        f_ofi = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        acts_o, q_ms = _timed("cp_oficio_query", lambda: get_pendientes_oficio(f_ofi))
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts_o)
        rows_o = [actuacion_to_pendiente_oficio_row(a, counts_by_eo=counts) for a in acts_o]
        p_ms = (time.perf_counter() - t0) * 1000
        print(
            f"cp_oficio_presenter: rows={len(rows_o)} ms={p_ms:.1f} "
            f"per_row={p_ms/len(rows_o) if rows_o else 0:.2f} total_ms={q_ms+p_ms:.1f}"
        )

        # CP — Reinspección oficio
        filas, q_ms = _timed(
            "cp_reinspeccion_query",
            lambda: list_pendientes_reinspeccion_oficio_filas(f_ofi),
        )
        t0 = time.perf_counter()
        acts_r = [f[0] for f in filas]
        counts = build_counts_by_eo_from_actuaciones(acts_r)
        rows_r = [
            reinspeccion_oficio_bandeja_row(act, counts_by_eo=counts, iniciador=ini, oficio=ofi)
            for act, ofi, ini in filas
        ]
        p_ms = (time.perf_counter() - t0) * 1000
        print(
            f"cp_reinspeccion_presenter: filas={len(rows_r)} ms={p_ms:.1f} "
            f"per_row={p_ms/len(rows_r) if rows_r else 0:.2f} total_ms={q_ms+p_ms:.1f}"
        )

        # CH — Recorrido global (cap 500)
        f_rec_g = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        acts_rec, q_ms = _timed(
            "ch_recorrido_global",
            lambda: list_comprobacion_recorrido(f_rec_g),
        )
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts_rec)
        rows_rec = [comprobacion_recorrido_resumen_row(a, counts_by_eo=counts) for a in acts_rec]
        p_ms = (time.perf_counter() - t0) * 1000
        print(
            f"ch_recorrido_global_presenter: rows={len(rows_rec)} ms={p_ms:.1f} "
            f"per_row={p_ms/len(rows_rec) if rows_rec else 0:.2f} total_ms={q_ms+p_ms:.1f}"
        )

        # CH — Recorrido mes con volumen (marzo 2026 si existe)
        f_rec_m = ActuacionesPendientesFilters.model_validate({"mes": 3, "anio": 2026})
        acts_rm, q_ms = _timed(
            "ch_recorrido_mes_3_2026",
            lambda: list_comprobacion_recorrido(f_rec_m),
        )
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts_rm)
        _ = [comprobacion_recorrido_resumen_row(a, counts_by_eo=counts) for a in acts_rm]
        p_ms = (time.perf_counter() - t0) * 1000
        print(f"ch_recorrido_mes_3_2026_presenter: rows={len(acts_rm)} ms={p_ms:.1f} total_ms={q_ms+p_ms:.1f}")

        # CH — filtros documentales individuales (recorrido)
        filters_doc = [
            ("acta", {"acta_comprobacion": "1"}),
            ("calle", {"calle_q": "san martin"}),
            ("contrib", {"contrib_q": "perez"}),
            ("oficio", {"oficio_numero": "202"}),
            ("expediente", {"expediente_numero": "123"}),
        ]
        for name, kw in filters_doc:
            acts_f, q_ms = _timed(
                f"ch_recorrido_filtro_{name}",
                lambda kw=kw: list_comprobacion_recorrido(
                    ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True}), **kw
                ),
            )
            t0 = time.perf_counter()
            counts = build_counts_by_eo_from_actuaciones(acts_f)
            _ = [comprobacion_recorrido_resumen_row(a, counts_by_eo=counts) for a in acts_f]
            p_ms = (time.perf_counter() - t0) * 1000
            print(f"  presenter_{name}: ms={p_ms:.1f} total={q_ms+p_ms:.1f}")

        # CP — numero_comprobacion en expediente (Python filter)
        f_num = ActuacionesPendientesFilters.model_validate(
            {**base_op, "numero_comprobacion": "1"}
        )
        acts_n, q_ms = _timed("cp_expediente_numero_comp", lambda: get_pendientes_expediente(f_num))
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts_n)
        _ = [
            actuacion_to_pendiente_expediente_row(
                a, counts_by_eo=counts, expediente_list_channel="comprobacion"
            )
            for a in acts_n
        ]
        p_ms = (time.perf_counter() - t0) * 1000
        print(f"cp_expediente_numero_comp_presenter: rows={len(acts_n)} total_ms={q_ms+p_ms:.1f}")


if __name__ == "__main__":
    main()
