"""
Permisos por rol de usuario (Inspector / RELEVADOR operativo).
"""

from __future__ import annotations

import re
from typing import Final

# Inspector (relevador): Completar trabajo + catálogos grid + perfil.
_RELEVADOR_ALLOWED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/actuaciones/completar-trabajo(?:/.*)?$"),
    re.compile(r"^/grid(?:/.*)?$"),
    re.compile(r"^/catalogos/rubros(?:/.*)?$"),
    re.compile(r"^/api/profile(?:/.*)?$"),
)

_RELEVADOR_DENIED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/actuaciones/pendientes(?:/.*)?$"),
    re.compile(r"^/api/admin(?:/.*)?$"),
)


def relevador_may_access(method: str, path: str) -> bool:
    """
    Indica si un usuario RELEVADOR puede acceder al path/método.

    Parámetros:
        method: HTTP method.
        path: request.path.

    Retorno:
        True si el acceso está permitido.
    """
    _ = (method or "GET").upper()
    p = path.rstrip("/") or "/"

    for rx in _RELEVADOR_DENIED:
        if rx.match(p):
            return False

    if p == "/actuaciones" or (
        p.startswith("/actuaciones/") and not p.startswith("/actuaciones/completar-trabajo")
    ):
        return False

    return any(rx.match(p) for rx in _RELEVADOR_ALLOWED)


def role_may_access_endpoint(role: str, method: str, path: str) -> bool:
    """
    Control de acceso por rol para endpoints JWT-protegidos.

    admin y usuario: sin restricción adicional (salvo guards específicos por ruta).
    relevador: allow-list acotada.
    """
    if role in ("admin", "usuario"):
        return True
    if role == "relevador":
        return relevador_may_access(method, path)
    return False
