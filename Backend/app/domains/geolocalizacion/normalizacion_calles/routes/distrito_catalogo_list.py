from __future__ import annotations

from flask import jsonify

from app.models import Distrito

from . import geolocalizacion_calles


@geolocalizacion_calles.get("/geolocalizacion/distritos/catalogo")
def list_distritos_catalogo():
    """
    Lista todos los distritos (catálogo DB, sin métricas de mapa).
    """
    rows = Distrito.query.order_by(Distrito.nombre.asc()).all()
    items = [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]
    return jsonify({"items": items}), 200
