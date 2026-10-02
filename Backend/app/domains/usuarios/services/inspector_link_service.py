from __future__ import annotations

from app.database import db
from app.models.inspector import Inspector
from app.models.user import User

INSPECTOR_ROLE = "relevador"


def resolve_inspector_nombre(user: User) -> str | None:
    """Nombre del inspector vinculado, si existe."""
    if user.inspector_id is None:
        return None
    insp = user.inspector
    return insp.nombre if insp else None


def _assert_inspector_linkable(inspector_id: int, *, exclude_user_id: int | None) -> Inspector:
    """
    Valida que el inspector exista y no esté vinculado a otra cuenta.

    Raises:
        ValueError: inspector inexistente o ya vinculado.
    """
    insp = Inspector.query.get(int(inspector_id))
    if insp is None:
        raise ValueError("Inspector no encontrado.")

    q = User.query.filter(User.inspector_id == int(inspector_id))
    if exclude_user_id is not None:
        q = q.filter(User.id != int(exclude_user_id))
    if q.first() is not None:
        raise ValueError("El inspector ya está vinculado a otra cuenta.")

    return insp


def apply_user_inspector_link(
    user: User,
    *,
    role: str,
    inspector_id: int | None,
    inspector_id_provided: bool,
) -> None:
    """
    Aplica reglas de vínculo cuenta ↔ Inspector.

    Regla al salir del rol Inspector (``relevador``): se limpia ``inspector_id``
    para evitar identidad operativa ambigua.

    Args:
        user: fila User en sesión ORM.
        role: rol efectivo tras create/update.
        inspector_id: id solicitado (puede ser None).
        inspector_id_provided: True si el payload incluyó la clave ``inspector_id``.

    Raises:
        ValueError: reglas de negocio incumplidas.
    """
    if role != INSPECTOR_ROLE:
        user.inspector_id = None
        return

    if inspector_id_provided:
        resolved = inspector_id
    else:
        resolved = user.inspector_id

    if resolved is None:
        raise ValueError("El rol Inspector requiere vincular un inspector activo.")

    _assert_inspector_linkable(int(resolved), exclude_user_id=user.id)
    user.inspector_id = int(resolved)
