"""V1.1-INSPECTOR.5 — Mis indicadores (GET acotado en /api/indicadores)."""

from __future__ import annotations

import pytest
from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.usuarios.security.inspector_scope_policy import CROSS_INSPECTOR_ACCESS_DETAIL
from app.domains.usuarios.security.role_permissions import relevador_may_access
from app.models import actuaciones_inspector

from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture

_INDICADORES_GET_PATHS = (
    "/api/indicadores/ejecutivo",
    "/api/indicadores/riesgo",
    "/api/indicadores/no-realizadas",
    "/api/indicadores/productividad",
)

_QUERY_RANGO = "desde=2026-06-01&hasta=2026-06-30"


def test_relevador_indicadores_allowlist_get_only() -> None:
    for path in _INDICADORES_GET_PATHS:
        assert relevador_may_access("GET", path)
        assert not relevador_may_access("POST", path)
        assert not relevador_may_access("PUT", path)
        assert not relevador_may_access("PATCH", path)
        assert not relevador_may_access("DELETE", path)
    assert not relevador_may_access("GET", "/api/indicadores/resumen")
    assert not relevador_may_access("GET", "/api/indicadores/pendientes")


@pytest.mark.parametrize("path", _INDICADORES_GET_PATHS)
def test_inspector_indicadores_cross_inspector_id_403(app, client, scope_fixture, path) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"{path}?{_QUERY_RANGO}&inspector_id={d['ins_b'].id}",
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == CROSS_INSPECTOR_ACCESS_DETAIL


@pytest.mark.parametrize("path", _INDICADORES_GET_PATHS)
def test_inspector_indicadores_ok_scoped(app, client, scope_fixture, path) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"{path}?{_QUERY_RANGO}", headers=headers)
    assert resp.status_code == 200


def _collect_productividad_inspector_ids(body: dict) -> set[int]:
    ids: set[int] = set()
    for key in ("inspectores_realizadas", "inspectores_no_realizadas", "actas_por_inspector"):
        for row in body.get(key) or []:
            ids.add(int(row["inspector_id"]))
    return ids


def test_inspector_productividad_solo_propio_inspector(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/api/indicadores/productividad?{_QUERY_RANGO}",
        headers=headers,
    )
    assert resp.status_code == 200
    ids = _collect_productividad_inspector_ids(resp.get_json())
    assert d["ins_b"].id not in ids
    if ids:
        assert ids == {d["ins_a"].id}


def test_inspector_b_no_ve_filas_de_a_en_productividad(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_b"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/api/indicadores/productividad?{_QUERY_RANGO}",
        headers=headers,
    )
    assert resp.status_code == 200
    ids = _collect_productividad_inspector_ids(resp.get_json())
    assert d["ins_a"].id not in ids
    if ids:
        assert ids == {d["ins_b"].id}


def test_indicadores_actuacion_compartida_ambos_inspectores(app, client, scope_fixture) -> None:
    d = scope_fixture
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=d["act_a"].id,
            inspector_id=d["ins_b"].id,
        )
    )
    db.session.commit()
    for user_key in ("user_a", "user_b"):
        token = create_access_token(identity=str(d[user_key].id))
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get(
            f"/api/indicadores/ejecutivo?{_QUERY_RANGO}",
            headers=headers,
        )
        assert resp.status_code == 200


def test_relevador_resumen_y_rutas_no_permitidas_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    for path in (
        "/api/indicadores/resumen",
        "/api/indicadores/pendientes",
    ):
        resp = client.get(f"{path}?{_QUERY_RANGO}", headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"


def test_usuario_indicadores_resumen_global(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["usuario"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/indicadores/resumen?{_QUERY_RANGO}", headers=headers)
    assert resp.status_code == 200


def test_usuario_productividad_sin_scope_forzado(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["usuario"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/api/indicadores/productividad?{_QUERY_RANGO}&inspector_id={d['ins_b'].id}",
        headers=headers,
    )
    assert resp.status_code == 200
