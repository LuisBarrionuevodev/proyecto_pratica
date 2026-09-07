"""PERF.1-B — desglose query vs post-proceso vs presenter."""
from __future__ import annotations

import time

from app import create_app
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import list_reinspeccion_notificacion_operativas
from app.domains.actuaciones.services.pendientes_service import (
    _apply_distrito_optional,
    _sin_expediente_notificacion_query,
    build_notificacion_expediente_bandeja_metrics,
    dedupe_actuaciones_canonicas_por_notificacion,
    get_pendientes_expediente,
)
from app.domains.actuaciones.utils.actuaciones_bandeja_eager import apply_bandeja_grid_eager
from app.domains.actuaciones.utils.notificacion_plazo_slice import filter_actuaciones_notificacion_por_plazo_slice
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import build_counts_by_eo_from_actuaciones


def ms_since(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def breakdown_plazo_slice(slice_name: str) -> None:
    filters = ActuacionesPendientesFilters.model_validate(
        {"source_type": "notificacion", "omitir_rango_fecha": True, "plazo_slice": slice_name}
    )
    t0 = time.perf_counter()
    q = apply_bandeja_grid_eager(_apply_distrito_optional(_sin_expediente_notificacion_query(filters), None))
    raw = q.order_by(q.column_descriptions[0]["entity"].id.desc()).all()
    t_raw = ms_since(t0)

    t0 = time.perf_counter()
    deduped = dedupe_actuaciones_canonicas_por_notificacion(raw)
    t_dedupe = ms_since(t0)

    t0 = time.perf_counter()
    sliced = filter_actuaciones_notificacion_por_plazo_slice(deduped, slice_name)
    t_slice = ms_since(t0)

    t0 = time.perf_counter()
    plazos, venc, pr = build_notificacion_expediente_bandeja_metrics(sliced)
    counts = build_counts_by_eo_from_actuaciones(sliced)
    rows = [
        actuacion_to_pendiente_expediente_row(
            a,
            plazos_por_notificacion=plazos,
            fecha_vencimiento_por_notificacion=venc,
            prorroga_dias_por_notificacion=pr,
            counts_by_eo=counts,
            expediente_list_channel="notificacion",
        )
        for a in sliced
    ]
    t_presenter = ms_since(t0)

    print(
        f"plazo_{slice_name}: raw={len(raw)} deduped={len(deduped)} final={len(rows)} "
        f"sql_eager_ms={t_raw:.1f} dedupe_ms={t_dedupe:.1f} slice_ms={t_slice:.1f} presenter_ms={t_presenter:.1f}"
    )


def breakdown_historial(label: str, filters_dict: dict) -> None:
    filters = ActuacionesPendientesFilters.model_validate({"source_type": "notificacion", **filters_dict})
    t0 = time.perf_counter()
    acts = get_pendientes_expediente(filters)
    t_query = ms_since(t0)

    from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

    t0 = time.perf_counter()
    counts = build_counts_by_eo_from_actuaciones(acts)
    _ = [actuacion_to_grid_row(a, counts_by_eo=counts) for a in acts]
    t_presenter = ms_since(t0)
    print(f"historial_{label}: n={len(acts)} get_pendientes_ms={t_query:.1f} grid_presenter_ms={t_presenter:.1f}")


def breakdown_reinspeccion() -> None:
    t0 = time.perf_counter()
    acts = list_reinspeccion_notificacion_operativas()
    t_sql = ms_since(t0)

    t0 = time.perf_counter()
    plazos, venc, pr = build_notificacion_expediente_bandeja_metrics(acts)
    counts = build_counts_by_eo_from_actuaciones(acts)
    _ = [
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
    t_presenter = ms_since(t0)
    print(f"reinspeccion: n={len(acts)} sql_ms={t_sql:.1f} presenter_ms={t_presenter:.1f}")


def main() -> None:
    app = create_app({"TESTING": True})
    with app.app_context():
        for s in ("en_plazo", "por_vencer"):
            breakdown_plazo_slice(s)
        breakdown_reinspeccion()
        breakdown_historial("global", {"omitir_rango_fecha": True})
        breakdown_historial("calle_san_martin", {"omitir_rango_fecha": True, "calle_q": "san martin"})
        breakdown_historial("num_notif", {"omitir_rango_fecha": True, "numero_notificacion": "0928"})
        breakdown_historial("contrib", {"omitir_rango_fecha": True, "contribuyente_q": "garcia"})
        breakdown_historial("motivo", {"omitir_rango_fecha": True, "motivo_q": "higiene"})


if __name__ == "__main__":
    main()
