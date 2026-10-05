"""
Permisos por rol de usuario.

- ``relevador``: perfil Inspector (actuaciones propias, completar trabajo, mapa/indicadores acotados).
- ``relevamiento``: perfil carga/gestión de relevamientos únicamente (sin módulos operativos).
"""

from __future__ import annotations

import re
from typing import Final

from flask import request

_RELEVADOR_COMPLETAR_TRABAJO_RX: Final[re.Pattern[str]] = re.compile(
    r"^/actuaciones/completar-trabajo(?:/.*)?$"
)
_PROFILE_RX: Final[re.Pattern[str]] = re.compile(r"^/api/profile(?:/.*)?$")
_RUBROS_CATALOGO_RX: Final[re.Pattern[str]] = re.compile(r"^/catalogos/rubros(?:/.*)?$")

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

_RELEVADOR_MAP_OPERATIVO_GET_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/map/operativo/pendientes",
        "/map/operativo/realizados",
    }
)

_RELEVADOR_DENIED: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^/actuaciones/pendientes(?:/.*)?$"),
    re.compile(r"^/api/admin(?:/.*)?$"),
)

_RELEVAMIENTO_RX: Final[re.Pattern[str]] = re.compile(r"^/relevamientos(?:/.*)?$")
_DENUNCIAS_RX: Final[re.Pattern[str]] = re.compile(r"^/api/denuncias(?:/.*)?$")

_RELEVAMIENTO_GRID_CATALOG_GET_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/grid/catalogs/relevadores",
        "/grid/catalogs/rubros",
    }
)

_GRID_MUTATION_RX: Final[re.Pattern[str]] = re.compile(
    r"^/grid/(?:batch/)?(?:start|validate-row|validate-batch|commit-row|commit-batch)$"
)

_RESTRICTED_ROLES: Final[frozenset[str]] = frozenset({"relevador", "relevamiento"})


def _normalize_path(path: str) -> str:
    return path.rstrip("/") or "/"


def _grid_request_kind() -> str | None:
    """Lee ``kind`` del body JSON en endpoints de grid (si existe)."""
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        raw = data.get("kind")
        if isinstance(raw, str):
            return raw.strip().lower()
    return None


def relevador_may_access(method: str, path: str) -> bool:
    """
    Indica si un usuario con rol ``relevador`` (Inspector) puede acceder al path/método.

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

    if _PROFILE_RX.match(p):
        return m in ("GET", "PATCH", "POST", "HEAD", "OPTIONS")

    if _RUBROS_CATALOGO_RX.match(p):
        return m in ("GET", "HEAD", "OPTIONS")

    if m == "GET" and p in _RELEVADOR_GRID_CATALOG_GET_PATHS:
        return True

    if p.startswith("/api/indicadores"):
        if p in _RELEVADOR_INDICADORES_GET_PATHS:
            return m in ("GET", "HEAD", "OPTIONS")
        return False

    if p.startswith("/map") or p.startswith("/api/map"):
        if p in _RELEVADOR_MAP_OPERATIVO_GET_PATHS:
            return m in ("GET", "HEAD", "OPTIONS")
        return False

    if p.startswith("/grid"):
        return False

    return False


def relevamiento_may_access(method: str, path: str) -> bool:
    """
    Perfil carga/gestión de relevamientos: allow-list mínima.

    Parámetros:
        method: HTTP method.
        path: request.path.

    Retorno:
        True si el acceso está permitido.

    Errores esperados: ninguno (función pura salvo lectura de body en mutaciones grid).
    """
    m = (method or "GET").upper()
    p = _normalize_path(path)

    if _DENUNCIAS_RX.match(p):
        return False

    if re.compile(r"^/api/admin(?:/.*)?$").match(p):
        return False

    if _PROFILE_RX.match(p):
        return m in ("GET", "PATCH", "POST", "HEAD", "OPTIONS")

    if _RELEVAMIENTO_RX.match(p):
        return m in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

    if _RUBROS_CATALOGO_RX.match(p):
        return m in ("GET", "HEAD", "OPTIONS")

    if m == "GET" and p in _RELEVAMIENTO_GRID_CATALOG_GET_PATHS:
        return True

    if _GRID_MUTATION_RX.match(p):
        if m not in ("POST", "HEAD", "OPTIONS"):
            return False
        return _grid_request_kind() == "relevamientos"

    if p.startswith("/grid"):
        return False

    return False


def role_may_access_endpoint(role: str, method: str, path: str) -> bool:
    """
    Control de acceso por rol para endpoints JWT-protegidos.

    admin y usuario: sin restricción adicional (salvo guards específicos por ruta).
    relevador: Inspector operativo (allow-list acotada).
    relevamiento: solo relevamientos, perfil y catálogos mínimos de carga.
    """
    if role in ("admin", "usuario"):
        return True
    if role == "relevador":
        return relevador_may_access(method, path)
    if role == "relevamiento":
        return relevamiento_may_access(method, path)
    return False


def role_requires_endpoint_allowlist(role: str) -> bool:
    """Indica si el rol debe pasar por ``role_may_access_endpoint`` en el guard JWT."""
    return role in _RESTRICTED_ROLES
