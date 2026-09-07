"""GESTIÓN-PERF.1-B — diagnóstico timing (solo lectura)."""
from __future__ import annotations

import time

from app import create_app
from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
)
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    get_pendientes_expediente,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.models import Actuaciones, Domicilio, OrdenTrabajo
from sqlalchemy import exists, and_, func


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
        total_noti = db.session.execute(
            db.text("SELECT COUNT(*) FROM actuaciones WHERE notificacion_id IS NOT NULL")
        ).scalar()

        print(f"total_actuaciones_con_notificacion={total_noti}")

        # BP — En plazo / Por vencer (mismo endpoint, distinto plazo_slice)
        for slice_name in ("en_plazo", "por_vencer"):
            f = ActuacionesPendientesFilters.model_validate(
                {
                    "source_type": "notificacion",
                    "omitir_rango_fecha": True,
                    "plazo_slice": slice_name,
                }
            )
            acts, q_ms = _timed(
                f"bp_query_{slice_name}",
                lambda: get_pendientes_expediente(f),
            )
            t0 = time.perf_counter()
            plazos, venc, pr = build_notificacion_expediente_bandeja_metrics(acts)
            counts = build_counts_by_eo_from_actuaciones(acts)
            rows = [
                actuacion_to_pendiente_expediente_row(
                    a,
                    plazos_por_notificacion=plazos,
                    fecha_vencimiento_por_notificacion=venc,
                    prorroga_dias_por_notificacion=pr,
                    counts_by_eo=counts,
                    expediente_list_channel="notificacion",
                )
                for a in acts
            ]
            p_ms = (time.perf_counter() - t0) * 1000
            print(f"bp_presenter_{slice_name}: rows={len(rows)} ms={p_ms:.1f} total_ms={q_ms+p_ms:.1f}")

        # BP — Pendiente reinspección
        acts_rein, q_ms = _timed(
            "bp_query_reinspeccion",
            lambda: list_reinspeccion_notificacion_operativas(),
        )
        t0 = time.perf_counter()
        plazos, venc, pr = build_notificacion_expediente_bandeja_metrics(acts_rein)
        counts = build_counts_by_eo_from_actuaciones(acts_rein)
        _ = [
            actuacion_to_pendiente_expediente_row(
                a,
                plazos_por_notificacion=plazos,
                fecha_vencimiento_por_notificacion=venc,
                prorroga_dias_por_notificacion=pr,
                counts_by_eo=counts,
                expediente_list_channel="notificacion",
            )
            for a in acts_rein
        ]
        print(f"bp_presenter_reinspeccion: ms={(time.perf_counter()-t0)*1000:.1f}")

        # BH — Historial mes actual (default range behavior without omitir)
        f_hist = ActuacionesPendientesFilters.model_validate(
            {"source_type": "notificacion", "mes": 1, "anio": 2026}
        )
        acts_h, q_ms = _timed("bh_query_mes_2026_01", lambda: get_pendientes_expediente(f_hist))
        t0 = time.perf_counter()
        counts = build_counts_by_eo_from_actuaciones(acts_h)
        from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

        for a in acts_h[:50]:
            actuacion_to_grid_row(a, counts_by_eo=counts)
        grid_sample_ms = (time.perf_counter() - t0) * 1000
        print(f"bh_presenter_grid_sample_50: ms={grid_sample_ms:.1f} extrap_acts={len(acts_h)}")

        # BH — global sin fecha
        f_global = ActuacionesPendientesFilters.model_validate(
            {"source_type": "notificacion", "omitir_rango_fecha": True}
        )
        _timed("bh_query_global_sin_fecha", lambda: get_pendientes_expediente(f_global))

        # Spike calle (EXISTS, no implementado en API operativa)
        calle_term = "san martin"
        t0 = time.perf_counter()
        q = (
            Actuaciones.query.filter(Actuaciones.notificacion_id.isnot(None))
            .filter(
                exists().where(
                    and_(
                        Domicilio.id == Actuaciones.domicilio_id,
                        func.lower(Domicilio.calle).contains(calle_term.lower()),
                    )
                )
            )
        )
        n_calle = q.count()
        print(f"spike_calle_count: n={n_calle} ms={(time.perf_counter()-t0)*1000:.1f}")

        # Spike OT
        ot = "092834"
        t0 = time.perf_counter()
        ot_row = OrdenTrabajo.query.filter(OrdenTrabajo.numero_acta == ot).first()
        if ot_row:
            n_ot = Actuaciones.query.filter(
                Actuaciones.notificacion_id.isnot(None),
                Actuaciones.orden_trabajo_id == ot_row.id,
            ).count()
        else:
            n_ot = 0
        print(f"spike_ot_count: n={n_ot} ms={(time.perf_counter()-t0)*1000:.1f}")


if __name__ == "__main__":
    main()
