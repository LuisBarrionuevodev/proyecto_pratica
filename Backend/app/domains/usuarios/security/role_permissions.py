"""
Permisos por rol de usuario (Inspector / RELEVADOR operativo).
"""

from __future__ import annotations

import re
from typing import Final

_RELEVADOR_COMPLETAR_TRABAJO_RX: Final[re.Pattern[str]] = re.compile(
    r"^/actuaciones/completar-trabajo(?:/.*)?$"
)
_RELEVADOR_PROFILE_RX: Final[re.Pattern[str]] = re.compile(r"^/api/profile(?:/.*)?$")
_RELEVADOR_RUBROS_RX: Final[re.Pattern[str]] = re.compile(r"^/catalogos/rubros(?:/.*)?$")

_RELEVADOR_GRID_CATALOG_GET_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/grid/catalogs/inspectores",
        "/grid/catalogs/motivos",
        "/grid/catalogs/contraproducencias",
        "/grid/catalogs/motivos-comprobacion",
        "/grid/catalogs/items-acta-inspeccion",
    }
)

_RELEVADOR_INDICADORES_GET_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/indicadores/ejecutivo",
        "/api/indicadores/riesgo",
        "/api/indicadores/no-realizadas",
        "/api/indicadores/productividad",
    }
)

_RELEVADOR_DENIED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/actuaciones/pendientes(?:/.*)?$"),
    re.compile(r"^/api/admin(?:/.*)?$"),
)


def _normalize_path(path: str) -> str:
    return path.rstrip("/") or "/"


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
    p = _normalize_path(path)

    for rx in _RELEVADOR_DENIED:
        if rx.match(p):
            return False

    if p == "/actuaciones":
        return m in ("GET", "HEAD", "OPTIONS")

    if p.startswith("/actuaciones/") and not p.startswith("/actuaciones/completar-trabajo"):
        return False

    if _RELEVADOR_COMPLETAR_TRABAJO_RX.match(p):
        return m in ("GET", "POST", "HEAD", "OPTIONS")

    if _RELEVADOR_PROFILE_RX.match(p):
        return m in ("GET", "PATCH", "POST", "HEAD", "OPTIONS")

    if _RELEVADOR_RUBROS_RX.match(p):
        return m in ("GET", "HEAD", "OPTIONS")

    if m == "GET" and p in _RELEVADOR_GRID_CATALOG_GET_PATHS:
        return True

    if p.startswith("/api/indicadores"):
        if p in _RELEVADOR_INDICADORES_GET_PATHS:
            return m in ("GET", "HEAD", "OPTIONS")
        return False

    if p.startswith("/grid"):
        return False

    return False


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
