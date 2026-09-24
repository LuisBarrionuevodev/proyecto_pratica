from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.domains.mapa_detalle.services.popup_service import get_popup_detail

mapa_detalle_api = Blueprint("mapa_detalle_api", __name__)


@mapa_detalle_api.get("/api/mapa-detalle/popup")
def get_popup_detail_route():
    """
    Devuelve detalle del popup del mapa para actuación/relevamiento.

    Query params:
        kind: "actuacion" | "relevamiento"
        id: id de entidad (acepta fallback a domicilio_id)

    Returns:
        Payload unificado para render del popup.

    Errores esperados:
        400: parámetros inválidos.
        404: entidad no encontrada.
    """
    kind = (request.args.get("kind") or "").strip().lower()
    raw_id = (request.args.get("id") or "").strip()

    if not kind or not raw_id:
        return jsonify({"detail": "Los parámetros 'kind' e 'id' son obligatorios."}), 400

    try:
        ref_id = int(raw_id)
    except ValueError:
        return jsonify({"detail": "El parámetro 'id' debe ser numérico."}), 400

    try:
        payload = get_popup_detail(kind=kind, ref_id=ref_id)
        return jsonify(payload), 200
    except ValueError as exc:
        message = str(exc)
        status = 400 if "kind inválido" in message.lower() else 404
        return jsonify({"detail": message}), status
