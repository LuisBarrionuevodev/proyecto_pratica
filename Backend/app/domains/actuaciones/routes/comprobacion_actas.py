"""
Actas de comprobación: reinspección por oficio y recorrido consultivo.
"""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
    iniciador_reinspeccion_to_row,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_comprobacion_recorrido,
    list_pendientes_reinspeccion_oficio,
)
from app.models import Actuaciones
from app.shared.errors import pydantic_errors_to_cell_map

from . import actuacion


def _filters_desde_request() -> ActuacionesPendientesFilters:
    raw = {k: (v if v else None) for k, v in request.args.to_dict().items()}
    solo_fecha = {k: raw[k] for k in ("desde", "hasta") if k in raw}
    return ActuacionesPendientesFilters.model_validate(solo_fecha)


@actuacion.get("/comprobacion/pendientes-reinspeccion-oficio")
def comprobacion_pendientes_reinspeccion_oficio():
    """
    Iniciadores REINSPECCION_OFICIO pendientes (oficio ya cargado; falta cerrar reinspección).
    """
    try:
        filters = _filters_desde_request()
        pairs = list_pendientes_reinspeccion_oficio(filters)
        items = [iniciador_reinspeccion_to_row(ini, act) for ini, act in pairs]
        return (
            jsonify(
                {
                    "items": items,
                    "meta": {
                        "total": len(items),
                        "desde": filters.desde.isoformat() if filters.desde else None,
                        "hasta": filters.hasta.isoformat() if filters.hasta else None,
                    },
                }
            ),
            200,
        )
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@actuacion.get("/comprobacion/recorrido")
def comprobacion_recorrido_list():
    """
    Tabla consultiva de recorrido documental (comprobación → expediente → oficio → reinspección).
    Filtros opcionales: contrib_q, calle_q, numero_q, acta_comprobacion,
    expediente_numero, oficio_numero, estado_recorrido, tipo_final (CUMPLE|NO_CUMPLE).
    """
    try:
        filters = _filters_desde_request()
        args = request.args
        acts = list_comprobacion_recorrido(
            filters,
            contrib_q=args.get("contrib_q"),
            calle_q=args.get("calle_q"),
            numero_q=args.get("numero_q"),
            acta_comprobacion=args.get("acta_comprobacion"),
            expediente_numero=args.get("expediente_numero"),
            oficio_numero=args.get("oficio_numero"),
            estado_recorrido=args.get("estado_recorrido"),
            tipo_final=args.get("tipo_final"),
        )
        items = [comprobacion_recorrido_resumen_row(a) for a in acts]
        return (
            jsonify(
                {
                    "items": items,
                    "meta": {
                        "total": len(items),
                        "desde": filters.desde.isoformat() if filters.desde else None,
                        "hasta": filters.hasta.isoformat() if filters.hasta else None,
                    },
                }
            ),
            200,
        )
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@actuacion.get("/comprobacion/recorrido/<int:actuacion_id>")
def comprobacion_recorrido_detalle_route(actuacion_id: int):
    """Detalle estructurado del recorrido para una actuación con comprobación."""
    try:
        act = Actuaciones.query.get(actuacion_id)
        if act is None:
            return jsonify({"detail": "Actuación no encontrada"}), 404
        if not act.comprobacion_id:
            return jsonify({"detail": "La actuación no tiene comprobación"}), 400
        payload = comprobacion_recorrido_detalle(act)
        return jsonify(payload), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
