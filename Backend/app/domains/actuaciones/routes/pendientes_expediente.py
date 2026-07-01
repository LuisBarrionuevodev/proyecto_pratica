from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_posterior_comprobacion_por_actuacion_id,
    build_reinspeccion_comprobacion_por_actuacion_id,
    get_pendientes_expediente,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.shared.errors import pydantic_errors_to_cell_map
from app.shared.perf_log import PerfTimer, perf_endpoint_log

from . import actuacion


@actuacion.get("/pendientes/expediente")
def pendientes_expediente_list():
    """
    Lista actuaciones pendientes de expediente con contrato estable.

    Query opcional ``omitir_rango_fecha=true``: sin ``desde``/``hasta`` no se aplica el rango por
    defecto (mes corriente); la consulta incluye todo pendiente sin filtro temporal en actuación.

    Cada ítem incluye ``source_type`` alineado con el filtro del GET (en ``notificacion``, filas con
    notificación pueden marcarse ``NOTIFICACION`` aunque la misma actuación tenga comprobación).

    Filtros documentales opcionales (solo ``source_type=notificacion``; subcadena insensible a mayúsculas):
    ``contribuyente_q``, ``calle_q``, ``numero_notificacion``, ``motivo_q``. Si no se envían, el
    comportamiento es el mismo que antes.

    Response:
      {
        "items": [...],
        "meta": {
          "total": int,
          "desde": "YYYY-MM-DD" | null,
          "hasta": "YYYY-MM-DD" | null,
          "source_type": "all|notificacion|comprobacion"
        }
      }
    """
    total_timer = PerfTimer()
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = ActuacionesPendientesFilters.model_validate(params)
        list_channel = (filters.source_type or "all").strip().lower()
        perf_key = f"{list_channel}.pendientes_expediente"

        query_timer = PerfTimer()
        acts = get_pendientes_expediente(filters)
        query_ms = query_timer.elapsed_ms()
        rows_base = len(acts)

        presenter_timer = PerfTimer()
        plazos_map, venc_map, prorroga_dias_map = build_notificacion_expediente_bandeja_metrics(acts)
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        posterior_map = build_posterior_comprobacion_por_actuacion_id(acts)
        reinspeccion_comp_map = build_reinspeccion_comprobacion_por_actuacion_id(acts)
        items = [
            actuacion_to_pendiente_expediente_row(
                a,
                plazos_por_notificacion=plazos_map,
                fecha_vencimiento_por_notificacion=venc_map,
                prorroga_dias_por_notificacion=prorroga_dias_map,
                counts_by_eo=counts_by_eo,
                posterior_por_actuacion_id=posterior_map,
                reinspeccion_comprobacion_por_actuacion_id=reinspeccion_comp_map,
                expediente_list_channel=list_channel,
            )
            for a in acts
        ]
        presenter_ms = presenter_timer.elapsed_ms()

        body = {
            "items": items,
            "meta": {
                "total": len(items),
                "desde": filters.desde.isoformat() if filters.desde else None,
                "hasta": filters.hasta.isoformat() if filters.hasta else None,
                "source_type": filters.source_type or "all",
            },
        }
        perf_endpoint_log(
            perf_key,
            rows_base=rows_base,
            rows_final=len(items),
            query_ms=query_ms,
            presenter_ms=presenter_ms,
            total_ms=total_timer.elapsed_ms(),
            payload=body,
            omitir_rango_fecha=params.get("omitir_rango_fecha"),
        )
        return jsonify(body), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
