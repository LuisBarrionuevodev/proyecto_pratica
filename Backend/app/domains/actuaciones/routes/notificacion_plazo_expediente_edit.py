"""
PATCH: edición controlada del expediente de prórroga (notificación).
"""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.notificacion_plazo_expediente_edit_in import (
    NotificacionProrrogaExpedientePatchIn,
)
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    update_notificacion_prorroga_expediente,
)

from . import actuacion


@actuacion.patch("/<int:actuacion_id>/notificacion/expedientes-prorroga/<int:expediente_id>")
def patch_notificacion_prorroga_expediente(actuacion_id: int, expediente_id: int):
    """
    Corrige número, fecha y plazo otorgado de un expediente ``PRORROGA_NOTIFICACION`` (misma notificación).

    Body JSON: ``numero_expediente``, ``fecha_expediente`` (YYYY-MM-DD), ``plazo_otorgado`` (entero >= 0).

    Al guardar se recalcula ``Notificacion.prorroga_dias`` (suma de plazos por expediente) y
    ``fecha_vencimiento``.

    Errores:
        400: reglas de negocio / validación.
        404: actuación o expediente inexistente.
        409: conflicto de unicidad número/año.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        body = NotificacionProrrogaExpedientePatchIn.model_validate(data)
    except ValidationError as e:
        err = e.errors()[0] if e.errors() else {}
        return jsonify({"detail": str(err.get("msg", "Datos inválidos"))}), 422
    try:
        out = update_notificacion_prorroga_expediente(
            actuacion_id,
            expediente_id,
            numero_expediente=body.numero_expediente,
            fecha_expediente=body.fecha_expediente,
            plazo_otorgado=body.plazo_otorgado,
        )
        ex = out["expediente"]
        noti = out["notificacion"]
        return jsonify(
            {
                "ok": True,
                "item": out["item"],
                "expediente_id": ex.id,
                "plazo_notificacion": {
                    "plazo_legal_dias": noti.plazo_dias,
                    "prorroga_total_dias": noti.prorroga_dias,
                    "fecha_notificacion": noti.fecha_notificacion.isoformat()
                    if noti.fecha_notificacion
                    else None,
                    "fecha_vencimiento": noti.fecha_vencimiento.isoformat()
                    if noti.fecha_vencimiento
                    else None,
                },
            }
        ), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409
