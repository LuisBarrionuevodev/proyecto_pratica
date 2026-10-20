"""MICROFIX V1.1-INSPECTOR-EDITAR-DATOS.1A — GET /grid/catalogs/tipos y deny grid masivo."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.domains.usuarios.security.role_permissions import relevador_may_access

from tests.test_hotfix_inspector_3a_grid import relevador_jwt_headers  # noqa: F401 — pytest fixture
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture

_PRODUCTION_TIPOS_CATALOG_PATH = "/grid/catalogs/tipos"


def test_relevador_may_get_tipos_catalog_for_editar_datos() -> None:
    assert relevador_may_access("GET", _PRODUCTION_TIPOS_CATALOG_PATH)
    assert not relevador_may_access("POST", _PRODUCTION_TIPOS_CATALOG_PATH)


def test_relevador_http_tipos_200_y_grid_mutaciones_403(client, relevador_jwt_headers) -> None:
    """Guard JWT real (sin mocks): misma ruta que falla en Railway con Inspector."""
    headers = relevador_jwt_headers
    tipos = client.get(_PRODUCTION_TIPOS_CATALOG_PATH, headers=headers)
    assert tipos.status_code == 200

    for path in ("/grid/validate-row", "/grid/start", "/grid/commit-row"):
        resp = client.post(path, headers=headers, json={})
        assert resp.status_code == 403
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"


def test_relevador_put_actuacion_ajena_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    act_id = d["act_b"].id
    resp = client.put(f"/actuaciones/{act_id}", headers=headers, json={"nombre_local": "X"})
    assert resp.status_code == 403
