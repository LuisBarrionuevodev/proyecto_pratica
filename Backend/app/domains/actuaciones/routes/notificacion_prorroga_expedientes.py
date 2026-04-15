"""
GET detalle documental: expedientes de prórroga por actuación (notificación).
"""

from __future__ import annotations

from flask import jsonify

from app.domains.actuaciones.services.notificacion_prorroga_expedientes_service import (
    list_notificacion_prorroga_expedientes_for_actuacion,
)

from . import actuacion


@actuacion.get("/<int:actuacion_id>/notificacion/expedientes-prorroga")
def get_notificacion_expedientes_prorroga(actuacion_id: int):
    """
    Lista expedientes ``PRORROGA_NOTIFICACION`` y estado consolidado de plazo de la notificación.

    No altera contratos de la bandeja ``GET /actuaciones/pendientes/expediente``; es lectura
    adicional para trazabilidad fina (modal / informes).

    Response 200:
        {
          "actuacion_id": int,
          "notificacion_id": int,
          "plazos_otorgados": int,
          "consolidado": {
            "plazo_dias": int,
            "prorroga_dias": int,
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
              "prorroga_dias_solicitada": null
            }
          ]
        }

    Errores:
        404: actuación no existe.
        400: actuación sin notificación u otra regla de negocio.
    """
    try:
        payload = list_notificacion_prorroga_expedientes_for_actuacion(actuacion_id)
        return jsonify(payload), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
