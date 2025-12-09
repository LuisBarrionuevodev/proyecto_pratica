from __future__ import annotations

from flask import Blueprint, jsonify

from app.models import Inspector, Rubro, Motivo

catalogos = Blueprint("catalogos", __name__)

@catalogos.get("/inspectores")
def listar_inspectores():
    items = Inspector.query.order_by(Inspector.nombre.asc()).all()
    return jsonify([{"id": i.id, "nombre": i.nombre} for i in items]), 200

@catalogos.get("/rubros")
def listar_rubros():
    items = Rubro.query.order_by(Rubro.nombre.asc()).all()
    return jsonify([{"id": r.id, "nombre": r.nombre} for r in items]), 200

@catalogos.get("/motivos")
def listar_motivos():
    items = Motivo.query.order_by(Motivo.nombre.asc()).all()
    return jsonify([{"id": m.id, "nombre": m.nombre} for m in items]), 200
