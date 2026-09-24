"""POST quitar acta desde canal Cargar actuación (modal)."""

from __future__ import annotations

from flask import jsonify, request

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas

from . import actuacion


@actuacion.post("/<int:actuacion_id>/quitar-acta")
def quitar_acta_canal_actas_route(actuacion_id: int):
    """
    Quita una acta operativa vinculada a la actuación (soft delete notif/comp; delete fila hija ins/cla/dec).

    Body JSON: ``{"tipo": "INSPECCION"|"NOTIFICACION"|"COMPROBACION"|"CLAUSURA"|"DECOMISO"}``.
    """
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")
    try:
        act = quitar_acta_canal_actas(actuacion_id, str(tipo))
        return jsonify(actuacion_to_grid_row(act)), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
