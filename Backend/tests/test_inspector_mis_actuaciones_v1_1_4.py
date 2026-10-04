"""V1.1-INSPECTOR.4 — Mis actuaciones (listado GET /actuaciones)."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.usuarios.security.inspector_scope_policy import CROSS_INSPECTOR_ACCESS_DETAIL
from app.domains.usuarios.security.role_permissions import relevador_may_access
from app.models import actuaciones_inspector

from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture


_QUERY_RANGO = "desde=2026-06-01&hasta=2026-06-30"


def test_relevador_role_permite_solo_get_actuaciones_raiz() -> None:
    assert relevador_may_access("GET", "/actuaciones")
    assert not relevador_may_access("POST", "/actuaciones")
    assert not relevador_may_access("GET", "/actuaciones/pendientes/domicilios")


def test_actuaciones_shared_visible_to_both_inspectors(app, client, scope_fixture) -> None:
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
        resp = client.get(f"/actuaciones?{_QUERY_RANGO}", headers=headers)
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.get_json()["items"]}
        assert d["act_a"].id in ids


def test_relevador_mutaciones_actuaciones_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    act_id = d["act_a"].id
    for method, path in (
        ("POST", "/actuaciones"),
        ("PUT", f"/actuaciones/{act_id}"),
        ("DELETE", f"/actuaciones/{act_id}"),
        ("GET", "/actuaciones/pendientes/summary"),
    ):
        if method == "DELETE":
            resp = client.delete(path, headers=headers)
        elif method == "POST":
            resp = client.post(path, headers=headers, json={})
        elif method == "PUT":
            resp = client.put(path, headers=headers, json={})
        else:
            resp = client.get(path, headers=headers)
        assert resp.status_code == 403
        assert resp.get_json()["detail"] == "No tiene permisos para esta acción"


def test_usuario_actuaciones_list_global(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["usuario"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/actuaciones?{_QUERY_RANGO}", headers=headers)
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.get_json()["items"]}
    assert d["act_a"].id in ids
    assert d["act_b"].id in ids


def test_inspector_cross_inspector_query_403(app, client, scope_fixture) -> None:
    d = scope_fixture
    token = create_access_token(identity=str(d["user_a"].id))
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(
        f"/actuaciones?{_QUERY_RANGO}&inspector_id={d['ins_b'].id}",
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.get_json()["detail"] == CROSS_INSPECTOR_ACCESS_DETAIL
