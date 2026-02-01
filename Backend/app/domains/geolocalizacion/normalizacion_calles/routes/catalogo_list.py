from __future__ import annotations

from flask import jsonify, request

from app.domains.geolocalizacion.normalizacion_calles.services.catalogo_list_service import (
    listar_catalogo_calles,
)

from . import geolocalizacion_calles


@geolocalizacion_calles.get("/geolocalizacion/calles/catalogo")
def list_catalogo_calles():
    """
    Lista calles del catálogo (para dropdowns).
    """
    try:
        search = request.args.get("search")
        limit_raw = request.args.get("limit")
        limit = int(limit_raw) if limit_raw else 20
        if limit < 1 or limit > 200:
            return jsonify({"detail": "limit debe estar entre 1 y 200"}), 400
        items = listar_catalogo_calles(search, limit=limit)
        return jsonify({"items": items}), 200
    except ValueError:
        return jsonify({"detail": "limit inválido"}), 400
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
