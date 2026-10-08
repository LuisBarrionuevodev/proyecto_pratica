from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.routes import actuacion
from app.domains.actuaciones.services.completar_trabajo_fotos_pendientes_count_service import (
    count_completar_trabajo_fotos_pendientes_inspector,
)
from app.domains.actuaciones.services.completar_trabajo_inspector_scope import (
    resolve_completar_trabajo_effective_inspector_id,
)


@actuacion.get("/completar-trabajo/pendientes/fotos-inspector")
@jwt_required()
def contar_fotos_pendientes_inspector():
    """
    Aviso persistente Inspector: trabajos propios con cierre guardado y fotos pendientes.
    """
    inspector_id = resolve_completar_trabajo_effective_inspector_id()
    if inspector_id is None:
        return jsonify({"count": 0}), 200
    count = count_completar_trabajo_fotos_pendientes_inspector(
        inspector_id_effective=int(inspector_id),
    )
    return jsonify({"count": count}), 200
