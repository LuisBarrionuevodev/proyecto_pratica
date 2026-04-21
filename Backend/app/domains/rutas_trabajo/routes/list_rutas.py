from __future__ import annotations

from datetime import date

from flask import jsonify, request

from app.domains.rutas_trabajo.presenters.ruta_presenters import ruta_trabajo_to_dict
from app.domains.rutas_trabajo.services.ruta_list_service import list_rutas_borrador

from . import rutas_trabajo


@rutas_trabajo.get("")
@rutas_trabajo.get("/")
def list_rutas():
    """
    Lista rutas en BORRADOR únicamente (para elegir y abrir en planificación).

    Query opcional: fecha_desde, fecha_hasta (YYYY-MM-DD), page, per_page.
    """
    raw_page = request.args.get("page", "1")
    raw_per = request.args.get("per_page", "50")
    try:
        page = int(raw_page)
        per_page = int(raw_per)
    except ValueError:
        return jsonify({"detail": "page y per_page deben ser enteros"}), 400

    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    fd = request.args.get("fecha_desde")
    fh = request.args.get("fecha_hasta")
    if fd:
        try:
            fecha_desde = date.fromisoformat(fd)
        except ValueError:
            return jsonify({"detail": "fecha_desde debe ser YYYY-MM-DD"}), 400
    if fh:
        try:
            fecha_hasta = date.fromisoformat(fh)
        except ValueError:
            return jsonify({"detail": "fecha_hasta debe ser YYYY-MM-DD"}), 400

    try:
        rows, total, per_efectivo = list_rutas_borrador(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            page=page,
            per_page=per_page,
        )
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    return jsonify(
        {
            "items": [ruta_trabajo_to_dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_efectivo,
            },
        }
    ), 200
