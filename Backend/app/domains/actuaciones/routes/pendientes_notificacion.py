from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.schemas.pendientes_notificacion_filters import PendientesNotificacionFilters
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
    enrich_pendiente_notificacion_row,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    _ESTADOS_INICIADOR_BANDEJA_REINSPECCION_NOTIF,
    list_reinspeccion_notificacion_operativas,
    materializacion_notificacion_vencida_on_read_enabled,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_reinspeccion_comprobacion_por_actuacion_id,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.models import IniciadorRuta
from app.shared.errors import pydantic_errors_to_cell_map
from app.shared.perf_log import PerfTimer, perf_endpoint_log

from . import actuacion


def _iniciador_id_por_actuacion_base(act_ids: list[int]) -> dict[int, int]:
    """
    Mapa ``actuacion_base_id`` → ``iniciador_id`` para filas PENDIENTE de reinspección por notificación.

    Parámetros:
        act_ids: ids de actuaciones INSPECCION devueltas por la cola operativa.

    Retorno:
        Dict actuacion_id → iniciador_ruta.id.
    """
    if not act_ids:
        return {}
    rows = (
        IniciadorRuta.query.filter(IniciadorRuta.actuacion_id.in_(act_ids))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
        .filter(IniciadorRuta.estado_iniciador.in_(_ESTADOS_INICIADOR_BANDEJA_REINSPECCION_NOTIF))
        .filter(IniciadorRuta.deleted_at.is_(None))
        .all()
    )
    out: dict[int, int] = {}
    for ini in rows:
        if ini.actuacion_id is not None:
            out[int(ini.actuacion_id)] = int(ini.id)
    return out


@actuacion.get("/pendientes-notificacion")
def get_pendientes_notificacion():
    """
    Lista operativa de reinspecciones por notificación vencida.

    Query opcional: ``desde``, ``hasta`` (``Actuaciones.fecha``), ``numero_notificacion``.

    Fase C: no ejecuta materialización salvo `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` (transitorio).
    En producción, el sync debe correr vía CLI / scheduler.
    """
    total_timer = PerfTimer()
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = PendientesNotificacionFilters.model_validate(params)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422

    if materializacion_notificacion_vencida_on_read_enabled():
        sync_iniciadores_reinspeccion_notificacion()

    query_timer = PerfTimer()
    acts = list_reinspeccion_notificacion_operativas(
        desde=filters.desde,
        hasta=filters.hasta,
        numero_notificacion=filters.numero_notificacion,
    )
    query_ms = query_timer.elapsed_ms()
    rows_base = len(acts)

    presenter_timer = PerfTimer()
    plazos_map, venc_map, prorroga_dias_map = build_notificacion_expediente_bandeja_metrics(acts)
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    rein_comp_map = build_reinspeccion_comprobacion_por_actuacion_id(acts)
    ini_by_act = _iniciador_id_por_actuacion_base([int(a.id) for a in acts])
    ini_ids = list(ini_by_act.values())
    estado_map = build_estado_operativo_pool_por_iniciador(ini_ids)
    payload = []
    for act in acts:
        row = actuacion_to_pendiente_expediente_row(
            act,
            plazos_por_notificacion=plazos_map,
            fecha_vencimiento_por_notificacion=venc_map,
            prorroga_dias_por_notificacion=prorroga_dias_map,
            counts_by_eo=counts_by_eo,
            reinspeccion_comprobacion_por_actuacion_id=rein_comp_map,
            expediente_list_channel="notificacion",
        )
        ini_id = ini_by_act.get(int(act.id))
        if ini_id is not None:
            row["iniciador_id"] = ini_id
            row["bandeja_row_key"] = f"{int(act.id)}-{ini_id}"
        row.setdefault("source_type", "NOTIFICACION")
        if act.domicilio_id is not None:
            row["domicilio_id"] = int(act.domicilio_id)
        enrich_pendiente_notificacion_row(row, estado_map=estado_map)
        payload.append(row)
    presenter_ms = presenter_timer.elapsed_ms()

    perf_endpoint_log(
        "notificaciones.pendientes_reinspeccion",
        rows_base=rows_base,
        rows_final=len(payload),
        query_ms=query_ms,
        presenter_ms=presenter_ms,
        total_ms=total_timer.elapsed_ms(),
        payload=payload,
    )
    return jsonify(payload), 200

