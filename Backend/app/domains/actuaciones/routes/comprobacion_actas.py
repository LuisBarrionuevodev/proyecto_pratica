"""
Actas de comprobación: reinspección por oficio y recorrido consultivo.
"""

from __future__ import annotations

from flask import jsonify, request
from pydantic import ValidationError
from sqlalchemy.orm import joinedload, selectinload

from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_detalle,
    comprobacion_recorrido_resumen_row,
    reinspeccion_oficio_bandeja_row,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_comprobacion_recorrido,
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
    enrich_pendiente_notificacion_row,
)
from app.models import Actuaciones, Domicilio
from app.shared.errors import pydantic_errors_to_cell_map
from app.shared.perf_log import PerfTimer, perf_endpoint_log

from . import actuacion


def _actuacion_for_recorrido_detalle(actuacion_id: int) -> Actuaciones | None:
    """Carga la actuación con relaciones usadas por ``actuacion_to_grid_row`` (evita lazy N+1 o filas sin inspectores)."""
    return (
        Actuaciones.query.options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            selectinload(Actuaciones.inspector),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.comprobacion),
        )
        .filter(Actuaciones.id == int(actuacion_id))
        .first()
    )


def _filters_desde_request() -> ActuacionesPendientesFilters:
    raw = {k: (v if v else None) for k, v in request.args.to_dict().items()}
    return ActuacionesPendientesFilters.model_validate(raw)


@actuacion.get("/comprobacion/pendientes-reinspeccion-oficio")
def comprobacion_pendientes_reinspeccion_oficio():
    """
    Reinspección por oficio: circuito documental completo y **aún sin ítem incorporado** en una ruta
    operativa (F3.6b). La existencia de ``IniciadorRuta`` no oculta la fila; solo un ``RutaItem`` activo
    (no borrado) en ``PUBLICADA`` / ``EN_CURSO`` (``BORRADOR`` sigue visible; STAB-3).
    """
    total_timer = PerfTimer()
    try:
        filters = _filters_desde_request()
        query_timer = PerfTimer()
        filas = list_pendientes_reinspeccion_oficio_filas(filters)
        query_ms = query_timer.elapsed_ms()
        rows_base = len(filas)

        presenter_timer = PerfTimer()
        acts = [f[0] for f in filas]
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        items = [
            reinspeccion_oficio_bandeja_row(
                act,
                counts_by_eo=counts_by_eo,
                iniciador=ini,
                oficio=ofi,
            )
            for act, ofi, ini in filas
        ]
        if filters.numero_comprobacion:
            q_num = filters.numero_comprobacion.replace(" ", "").lower()
            items = [
                row
                for row in items
                if q_num in (row.get("acta_comprobacion_num") or "").replace(" ", "").lower()
            ]
        ini_ids = [
            int(row["iniciador_id"])
            for row in items
            if int(row.get("iniciador_id") or 0) > 0
        ]
        estado_map = build_estado_operativo_pool_por_iniciador(ini_ids)
        for row in items:
            ini_id = int(row.get("iniciador_id") or 0)
            if ini_id <= 0:
                row["estado_operativo_pool"] = "pendiente"
                continue
            enrich_pendiente_notificacion_row(row, estado_map=estado_map)
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
            "comprobacion.pendientes_reinspeccion_oficio",
            rows_base=rows_base,
            rows_final=len(items),
            query_ms=query_ms,
            presenter_ms=presenter_ms,
            total_ms=total_timer.elapsed_ms(),
            payload=body,
            omitir_rango_fecha=request.args.get("omitir_rango_fecha"),
        )
        return jsonify(body), 200
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
    total_timer = PerfTimer()
    try:
        filters = _filters_desde_request()
        args = request.args
        query_timer = PerfTimer()
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
        query_ms = query_timer.elapsed_ms()
        rows_base = len(acts)

        presenter_timer = PerfTimer()
        counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
        items = [comprobacion_recorrido_resumen_row(a, counts_by_eo=counts_by_eo) for a in acts]
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
            "comprobacion.recorrido",
            rows_base=rows_base,
            rows_final=len(items),
            query_ms=query_ms,
            presenter_ms=presenter_ms,
            total_ms=total_timer.elapsed_ms(),
            payload=body,
        )
        return jsonify(body), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500


@actuacion.get("/comprobacion/recorrido/<int:actuacion_id>")
def comprobacion_recorrido_detalle_route(actuacion_id: int):
    """Detalle estructurado del recorrido para una actuación con comprobación."""
    total_timer = PerfTimer()
    try:
        act = _actuacion_for_recorrido_detalle(actuacion_id)
        if act is None:
            return jsonify({"detail": "Actuación no encontrada"}), 404
        if not act.comprobacion_id:
            return jsonify({"detail": "La actuación no tiene comprobación"}), 400
        presenter_timer = PerfTimer()
        payload = comprobacion_recorrido_detalle(act)
        presenter_ms = presenter_timer.elapsed_ms()
        perf_endpoint_log(
            "comprobacion.recorrido_detalle",
            rows_base=1,
            rows_final=1,
            query_ms=total_timer.elapsed_ms() - presenter_ms,
            presenter_ms=presenter_ms,
            total_ms=total_timer.elapsed_ms(),
            payload=payload,
            actuacion_id=actuacion_id,
        )
        return jsonify(payload), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
