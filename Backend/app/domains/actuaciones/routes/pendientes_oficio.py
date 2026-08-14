from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_pendiente_oficio_row,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
    enrich_pendiente_notificacion_row,
)
from app.domains.actuaciones.services.pendientes_service import get_pendientes_oficio
from app.models import IniciadorRuta
from app.shared.errors import pydantic_errors_to_cell_map
from app.shared.perf_log import PerfTimer, perf_endpoint_log

from . import actuacion


@actuacion.get("/pendientes/oficio")
def pendientes_oficio_list():
    """
    Lista actuaciones en estado "esperando oficio".

    Response:
      {
        "items": [...],
        "meta": {"total": int, "desde": "YYYY-MM-DD"|null, "hasta": "YYYY-MM-DD"|null}
      }
    """
    total_timer = PerfTimer()
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = ActuacionesPendientesFilters.model_validate(params)

        query_timer = PerfTimer()
        acts = get_pendientes_oficio(filters)
        query_ms = query_timer.elapsed_ms()
        rows_base = len(acts)

        presenter_timer = PerfTimer()
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        act_ids = [int(a.id) for a in acts]
        ini_by_act: dict[int, int] = {}
        if act_ids:
            ini_rows = (
                IniciadorRuta.query.filter(IniciadorRuta.actuacion_id.in_(act_ids))
                .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
                .filter(IniciadorRuta.deleted_at.is_(None))
                .order_by(IniciadorRuta.id.desc())
                .all()
            )
            for ini in ini_rows:
                aid = int(ini.actuacion_id)
                if aid not in ini_by_act:
                    ini_by_act[aid] = int(ini.id)
        estado_map = build_estado_operativo_pool_por_iniciador(list(ini_by_act.values()))
        items = []
        for a in acts:
            row = actuacion_to_pendiente_oficio_row(a, counts_by_eo=counts_by_eo)
            ini_id = ini_by_act.get(int(a.id))
            if ini_id:
                row["iniciador_id"] = ini_id
                enrich_pendiente_notificacion_row(row, estado_map=estado_map)
            else:
                enrich_pendiente_notificacion_row(row, estado_map=None, force_no_elegible=True)
            items.append(row)
        presenter_ms = presenter_timer.elapsed_ms()

        body = {
            "items": items,
            "meta": {
                "total": len(items),
                "desde": filters.desde.isoformat() if filters.desde else None,
                "hasta": filters.hasta.isoformat() if filters.hasta else None,
            },
        }
        perf_endpoint_log(
            "comprobacion.pendientes_oficio",
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
