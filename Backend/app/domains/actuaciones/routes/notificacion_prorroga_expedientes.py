"""
GET detalle documental: expedientes de prórroga por actuación (notificación).
"""

from __future__ import annotations

from flask import jsonify

from app.domains.actuaciones.services.notificacion_prorroga_expedientes_service import (
    list_notificacion_prorroga_expedientes_for_actuacion,
)
from app.shared.perf_log import PerfTimer, perf_endpoint_log

from . import actuacion


@actuacion.get("/<int:actuacion_id>/notificacion/expedientes-prorroga")
def get_notificacion_expedientes_prorroga(actuacion_id: int):
    """
    Lista expedientes ``PRORROGA_NOTIFICACION`` y estado de plazo/vencimiento de la notificación.

    No altera contratos de la bandeja ``GET /actuaciones/pendientes/expediente``; es lectura
    adicional para trazabilidad fina (modal / informes).

    Response 200:
        {
          "actuacion_id": int,
          "notificacion_id": int,
          "plazos_otorgados": int,
          "plazo_notificacion": {
            "plazo_legal_dias": int,
            "prorroga_total_dias": int,
            "fecha_notificacion": "YYYY-MM-DD" | null,
            "fecha_vencimiento": "YYYY-MM-DD" | null
          },
          "items": [
            {
              "id": int,
              "numero_expediente": str,
              "anio": str,
              "fecha_expediente": "YYYY-MM-DD" | null,
              "created_at": ISO-8601,
              "tipo_expediente": "PRORROGA_NOTIFICACION",
              "plazo_otorgado": int | null
            }
          ],
          "edicion": {
            "puede_editar_expediente_prorroga": bool,
            "notificacion_usada_como_iniciador": bool,
            "motivos_bloqueo_expediente": [str, ...]
          }
        }

    Errores:
        404: actuación no existe.
        400: actuación sin notificación u otra regla de negocio.
    """
    total_timer = PerfTimer()
    try:
        presenter_timer = PerfTimer()
        payload = list_notificacion_prorroga_expedientes_for_actuacion(actuacion_id)
        presenter_ms = presenter_timer.elapsed_ms()
        items_n = len(payload.get("items") or []) if isinstance(payload, dict) else 0
        perf_endpoint_log(
            "notificaciones.expedientes_prorroga_detalle",
            rows_base=items_n,
            rows_final=items_n,
            query_ms=0.0,
            presenter_ms=presenter_ms,
            total_ms=total_timer.elapsed_ms(),
            payload=payload,
            actuacion_id=actuacion_id,
        )
        return jsonify(payload), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
