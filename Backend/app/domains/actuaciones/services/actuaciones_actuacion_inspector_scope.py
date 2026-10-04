from __future__ import annotations

from app.database import db
from app.domains.usuarios.security.inspector_scope_policy import (
    InspectorScopeError,
    resolve_effective_inspector_id,
)
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE
from app.domains.usuarios.services.inspector_query_scope import scope_actuaciones_to_inspector
from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.models import Actuaciones

_INSPECTOR_ACTUACION_DENIED = "No tiene permisos para consultar o editar esta actuación."


def assert_inspector_puede_acceder_actuacion(actuacion_id: int) -> None:
    """
    Impide que un Inspector (rol relevador) acceda a actuaciones no asignadas.

    Parámetros:
        actuacion_id: id de actuación.

    Errores:
        InspectorScopeError: 403 si el inspector de sesión no está vinculado a la actuación.
    """
    user = resolve_user_from_identity()
    if user is None or user.role != INSPECTOR_ROLE:
        return
    eff = resolve_effective_inspector_id(None, user=user)
    q = db.session.query(Actuaciones).filter(Actuaciones.id == int(actuacion_id))
    q = scope_actuaciones_to_inspector(q, int(eff))
    if q.first() is None:
        raise InspectorScopeError(_INSPECTOR_ACTUACION_DENIED, status_code=403)
