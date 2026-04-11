from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    get_pendientes_expediente,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.shared.errors import pydantic_errors_to_cell_map

from . import actuacion


@actuacion.get("/pendientes/expediente")
def pendientes_expediente_list():
    """
    Lista actuaciones pendientes de expediente con contrato estable.

    Query opcional ``omitir_rango_fecha=true``: sin ``desde``/``hasta`` no se aplica el rango por
    defecto (mes corriente); la consulta incluye todo pendiente sin filtro temporal en actuación.

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
    try:
        params = {k: (v if v else None) for k, v in request.args.to_dict().items()}
        filters = ActuacionesPendientesFilters.model_validate(params)
        acts = get_pendientes_expediente(filters)
        plazos_map, venc_map = build_notificacion_expediente_bandeja_metrics(acts)
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        items = [
            actuacion_to_pendiente_expediente_row(
                a,
                plazos_por_notificacion=plazos_map,
                fecha_vencimiento_por_notificacion=venc_map,
                counts_by_eo=counts_by_eo,
            )
            for a in acts
        ]
        return jsonify({
            "items": items,
            "meta": {
                "total": len(items),
                "desde": filters.desde.isoformat() if filters.desde else None,
                "hasta": filters.hasta.isoformat() if filters.hasta else None,
                "source_type": filters.source_type or "all",
            },
        }), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
