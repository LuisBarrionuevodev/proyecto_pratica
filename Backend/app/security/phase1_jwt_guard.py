"""
JWT por fases en el API JSON.

- Fase 1: mutaciones y escrituras sensibles (actuaciones, grid commit, geo POST, rutas_trabajo CUD,
  sync notificaciones vencidas).
- PR-A (lecturas): GET/HEAD en `/actuaciones/*`, `/api/denuncias*`, `/rutas-trabajo/*`.
- PR-B (lecturas): GET/HEAD en `/relevamientos/*`.
- PR-C1 (lecturas): GET/HEAD en `/map/*`, `/api/map/*`, `/geo/*`, `/geolocalizacion/*`.
- PR-C2 (lecturas): GET/HEAD en `/grid/catalogs/*`.
- Indicadores: GET/HEAD en `/api/indicadores/*`.

Qué hace: `before_request` con `verify_jwt_in_request` cuando la ruta/método coincide.
Parámetros: app Flask (tras `init_jwt`).
Errores: 401 JSON si falta o es inválido el Bearer.

Excluye: OPTIONS, `/static/*`, login y password-reset públicos.
"""

from __future__ import annotations

import re
from typing import Final

from flask import Flask, jsonify, request
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException

# Rutas públicas (normalizadas sin barra final, salvo raíz).
_PUBLIC_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/auth/login",
        "/api/auth/password-reset/request",
        "/api/auth/password-reset/confirm",
    }
)

# (método HTTP, regex sobre request.path)
_PHASE1_METHOD_PATH: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("POST", re.compile(r"^/actuaciones/?$")),
    ("PUT", re.compile(r"^/actuaciones/\d+$")),
    ("PATCH", re.compile(r"^/actuaciones/\d+$")),
    ("DELETE", re.compile(r"^/actuaciones/\d+$")),
    ("POST", re.compile(r"^/actuaciones/\d+/expediente$")),
    ("POST", re.compile(r"^/actuaciones/\d+/oficio$")),
    ("POST", re.compile(r"^/actuaciones/completar-trabajo/cerrar/\d+$")),
    ("POST", re.compile(r"^/actuaciones/\d+/epicollect/import$")),
    ("POST", re.compile(r"^/actuaciones/\d+/epicollect/import-from-api$")),
    (
        "POST",
        re.compile(r"^/actuaciones/pendientes/sync-notificaciones-vencidas$"),
    ),
    ("POST", re.compile(r"^/grid/commit-batch$")),
    ("POST", re.compile(r"^/grid/commit-row$")),
    (
        "POST",
        re.compile(
            r"^/geolocalizacion/calles/(?:normalize/\d+|normalize-pending|set-canon/\d+|"
            r"set-esquina/\d+|set-numero/\d+|guardar-nomenclatura/\d+)$"
        ),
    ),
    ("POST", re.compile(r"^/geolocalizacion/geocode/\d+$")),
    ("POST", re.compile(r"^/geolocalizacion/geocode-pending$")),
    ("POST", re.compile(r"^/geo/\d+/(?:retry|manual|reverse)$")),
    ("POST", re.compile(r"^/api/map/geocode/manual$")),
)

_RUTAS_TRABAJO_MUTATION: Final[re.Pattern[str]] = re.compile(
    r"^/rutas-trabajo(?:/.*)?$"
)
_MUTATION_METHODS: Final[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_READ_METHODS_PROTECTED: Final[frozenset[str]] = frozenset({"GET", "HEAD"})


def _normalize_path(path: str) -> str:
    p = path.rstrip("/")
    return p if p else "/"


def _is_public_path(path: str) -> bool:
    return _normalize_path(path) in _PUBLIC_PATHS


def _phase1_requires_jwt(method: str, path: str) -> bool:
    if method in _MUTATION_METHODS and _RUTAS_TRABAJO_MUTATION.match(path):
        return True
    for m, rx in _PHASE1_METHOD_PATH:
        if m == method and rx.match(path):
            return True
    return False


def _pr_a_requires_jwt(method: str, path: str) -> bool:
    """
    PR-A: lecturas de actuaciones, denuncias y rutas-trabajo.

    Incluye `GET /actuaciones/completar-trabajo/*`.
    """
    if method not in _READ_METHODS_PROTECTED:
        return False
    if path == "/actuaciones" or path.startswith("/actuaciones/"):
        return True
    if path == "/api/denuncias" or path.startswith("/api/denuncias/"):
        return True
    if path == "/rutas-trabajo" or path.startswith("/rutas-trabajo/"):
        return True
    return False


def _pr_b_requires_jwt(method: str, path: str) -> bool:
    """PR-B: lecturas de relevamientos."""
    if method not in _READ_METHODS_PROTECTED:
        return False
    return path == "/relevamientos" or path.startswith("/relevamientos/")


def _pr_c1_requires_jwt(method: str, path: str) -> bool:
    """
    PR-C1: lecturas de mapas, geo operativo y geolocalización (calles/distritos catálogo).

    Incluye `GET /api/map/*` (alias p. ej. pendientes) además de `/map/*`.
    """
    if method not in _READ_METHODS_PROTECTED:
        return False
    if path == "/map" or path.startswith("/map/"):
        return True
    if path == "/api/map" or path.startswith("/api/map/"):
        return True
    if path == "/geo" or path.startswith("/geo/"):
        return True
    if path.startswith("/geolocalizacion/"):
        return True
    return False


def _pr_c2_requires_jwt(method: str, path: str) -> bool:
    """PR-C2: catálogos del grid (dropdowns / batch)."""
    if method not in _READ_METHODS_PROTECTED:
        return False
    return path == "/grid/catalogs" or path.startswith("/grid/catalogs/")


def _indicadores_requires_jwt(method: str, path: str) -> bool:
    """Dashboard operativo: indicadores agregados."""
    if method not in _READ_METHODS_PROTECTED:
        return False
    return path == "/api/indicadores" or path.startswith("/api/indicadores/")


def _establecimientos_operativos_requires_jwt(method: str, path: str) -> bool:
    """Lecturas de fichas operativas (listado, detalle, historial de actuaciones)."""
    if method not in _READ_METHODS_PROTECTED:
        return False
    return path == "/establecimientos-operativos" or path.startswith("/establecimientos-operativos/")


def _requires_jwt(method: str, path: str) -> bool:
    return (
        _phase1_requires_jwt(method, path)
        or _pr_a_requires_jwt(method, path)
        or _pr_b_requires_jwt(method, path)
        or _pr_c1_requires_jwt(method, path)
        or _pr_c2_requires_jwt(method, path)
        or _indicadores_requires_jwt(method, path)
        or _establecimientos_operativos_requires_jwt(method, path)
    )


def register_phase1_jwt_guard(app: Flask) -> None:
    """
    Registra el guard JWT (fase 1 + PR-A..C2 + indicadores lecturas indicadas).
    """

    @app.before_request
    def _phase1_jwt_before_request() -> tuple | None:
        if request.method == "OPTIONS":
            return None

        path = request.path or ""

        if path.startswith("/static/"):
            return None

        if _is_public_path(path):
            return None

        if not _requires_jwt(request.method, path):
            return None

        try:
            verify_jwt_in_request()
        except JWTExtendedException:
            return jsonify({"detail": "Autenticación requerida o token inválido."}), 401

        from app.domains.usuarios.security.decorators import resolve_user_from_identity
        from app.domains.usuarios.security.role_permissions import role_may_access_endpoint

        user = resolve_user_from_identity()
        if user and user.is_active and user.role == "relevador":
            if not role_may_access_endpoint(user.role, request.method, path):
                return jsonify({"detail": "No tiene permisos para esta acción"}), 403

        return None
