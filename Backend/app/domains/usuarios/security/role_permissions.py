"""
Permisos por rol de usuario (HOTFIX-CIERRE-DIA — RELEVADOR).
"""

from __future__ import annotations

import re
from typing import Final

# Prefijos permitidos para RELEVADOR (carga relevamientos/denuncias, cargar actuación, gestión RD).
_RELEVADOR_ALLOWED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/relevamientos(?:/.*)?$"),
    re.compile(r"^/api/denuncias(?:/.*)?$"),
    re.compile(r"^/grid(?:/.*)?$"),
    re.compile(r"^/catalogos/rubros(?:/.*)?$"),
    re.compile(r"^/api/profile(?:/.*)?$"),
    re.compile(r"^/actuaciones/?$"),
    re.compile(r"^/actuaciones/\d+$"),
)

# Bloqueos explícitos aunque coincidan con prefijos amplios.
_RELEVADOR_DENIED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/actuaciones/pendientes(?:/.*)?$"),
    re.compile(r"^/actuaciones/completar-trabajo(?:/.*)?$"),
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
    m = (method or "GET").upper()
    p = path.rstrip("/") or "/"

    for rx in _RELEVADOR_DENIED:
        if rx.match(p):
            return False

    # Listado/edición masiva de actuaciones: solo carga vía POST /actuaciones y grid.
    if p == "/actuaciones" and m != "POST":
        return False
    if re.match(r"^/actuaciones/\d+$", p) and m in ("GET", "DELETE"):
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
