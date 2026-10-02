from __future__ import annotations

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE
from app.domains.usuarios.services.inspector_query_scope import scope_ruta_items_to_inspector
from app.models import RutaItem


class RutaItemAccessError(Exception):
    """Error de autorización sobre un ``RutaItem`` (401/403/404)."""

    def __init__(self, message: str, *, status_code: int = 403) -> None:
        super().__init__(message)
        self.status_code = status_code


RUTA_ITEM_FORBIDDEN_DETAIL = "No tiene permisos para acceder a este trabajo."


def assert_current_user_can_access_ruta_item(ruta_item_id: int) -> RutaItem:
    """
    Verifica que el usuario autenticado pueda operar sobre el ``RutaItem``.

    Parámetros:
        ruta_item_id: id del ítem de ruta.

    Retorno:
        ``RutaItem`` activo si el acceso está permitido.

    Errores:
        RutaItemAccessError: 401 sin sesión; 404 inexistente; 403 Inspector fuera de grupo.
    """
    user = resolve_user_from_identity()
    if user is None or not user.is_active:
        raise RutaItemAccessError("No autorizado.", status_code=401)

    item = RutaItem.query.filter(
        RutaItem.id == int(ruta_item_id),
        RutaItem.deleted_at.is_(None),
    ).first()
    if item is None:
        raise RutaItemAccessError("Ítem de ruta no encontrado.", status_code=404)

    if user.role == INSPECTOR_ROLE:
        if user.inspector_id is None or user.inspector is None:
            raise RutaItemAccessError(
                "La cuenta no tiene un inspector vinculado.",
                status_code=403,
            )
        scoped = scope_ruta_items_to_inspector(
            RutaItem.query.filter(RutaItem.id == int(ruta_item_id)),
            int(user.inspector_id),
        ).first()
        if scoped is None:
            raise RutaItemAccessError(RUTA_ITEM_FORBIDDEN_DETAIL, status_code=403)

    return item
