"""
HOTFIX V1.1-RELEVADORES.1 — batch grid acepta Apellido, Nombre y Nombre Apellido.
"""

from __future__ import annotations

import pytest

from app.domains.relevamientos.utils.relevador_display import relevador_etiqueta_catalogo
from app.models import Domicilio, Relevamiento
from tests.relevamiento_test_helpers import (
    get_or_create_test_relevador,
    get_test_rubro,
    require_relevadores_migration,
    uniq,
)


@pytest.fixture
def require_rel_migration(app_ctx):
    require_relevadores_migration()


def _grid_row(*, inspector: str, calle: str | None = None, numero: str = "401") -> dict:
    rub = get_test_rubro()
    return {
        "Inspector": inspector,
        "Calle": calle or uniq("RelGrid"),
        "Número": numero,
        "Rubro": rub.nombre,
    }


def _start_batch(client, auth_headers) -> str:
    resp = client.post(
        "/grid/start",
        headers=auth_headers,
        json={"kind": "relevamientos"},
    )
    assert resp.status_code == 200
    return resp.get_json()["batch_id"]


def test_validate_row_apellido_nombre_ok(client, auth_headers, require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    label = relevador_etiqueta_catalogo(rel.nombre)
    batch_id = _start_batch(client, auth_headers)
    resp = client.post(
        "/grid/validate-row",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "row_id": "r1",
            "row": _grid_row(inspector=label),
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["ok"] is True, body.get("errors")


def test_validate_row_nombre_apellido_ok(client, auth_headers, require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    batch_id = _start_batch(client, auth_headers)
    resp = client.post(
        "/grid/validate-row",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "row_id": "r1",
            "row": _grid_row(inspector=rel.nombre),
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["ok"] is True, body.get("errors")


def test_validate_batch_apellido_nombre_ok(client, auth_headers, require_rel_migration) -> None:
    rel = get_or_create_test_relevador()
    label = relevador_etiqueta_catalogo(rel.nombre)
    batch_id = _start_batch(client, auth_headers)
    row = _grid_row(inspector=label)
    resp = client.post(
        "/grid/validate-batch",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "rows": [{"row_id": "b1", "row": row}],
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["results"][0]["ok"] is True, body["results"][0].get("errors")


def test_validate_row_relevador_vacio(client, auth_headers, require_rel_migration) -> None:
    batch_id = _start_batch(client, auth_headers)
    row = _grid_row(inspector="")
    row.pop("Inspector")
    resp = client.post(
        "/grid/validate-row",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "row_id": "r1",
            "row": row,
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["ok"] is False
    assert body["errors"].get("Inspector") == "Debe indicar un relevador."


def test_validate_row_relevador_inexistente(client, auth_headers, require_rel_migration) -> None:
    batch_id = _start_batch(client, auth_headers)
    resp = client.post(
        "/grid/validate-row",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "row_id": "r1",
            "row": _grid_row(inspector="No Existe Relevador XYZ"),
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["ok"] is False
    assert body["errors"].get("Inspector") == "Relevador no encontrado. Seleccioná uno del catálogo."


def test_commit_batch_apellido_nombre_persiste(
    client, auth_headers, app_ctx, require_rel_migration
) -> None:
    rel = get_or_create_test_relevador()
    expected_nombre = rel.nombre
    label = relevador_etiqueta_catalogo(rel.nombre)
    calle = uniq("RelCommit")
    batch_id = _start_batch(client, auth_headers)
    v = client.post(
        "/grid/validate-row",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "row_id": "c1",
            "row": _grid_row(inspector=label, calle=calle),
        },
    )
    assert v.get_json()["ok"] is True, v.get_json()
    normalized = v.get_json()["normalized"]
    resp = client.post(
        "/grid/commit-batch",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "rows": [{"row_id": "c1", "normalized": normalized}],
        },
    )
    body = resp.get_json()
    assert resp.status_code == 200, body
    assert body["results"][0]["ok"] is True, body["results"][0]

    dom = Domicilio.query.filter_by(calle=calle).order_by(Domicilio.id.desc()).first()
    assert dom is not None
    created = Relevamiento.query.filter_by(domicilio_id=dom.id).order_by(Relevamiento.id.desc()).first()
    assert created is not None
    from app.domains.relevamientos.utils.relevador_display import relevador_nombres_equivalentes

    assert len(created.relevadores) == 1
    assert relevador_nombres_equivalentes(created.relevadores[0].nombre, expected_nombre)


def test_catalog_relevadores_formato_y_orden(client, auth_headers, require_rel_migration) -> None:
    from app.domains.relevamientos.utils.relevador_display import relevador_sort_key

    resp = client.get("/grid/catalogs/relevadores", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    assert items
    keys = [relevador_sort_key(i["nombre"]) for i in items]
    assert keys == sorted(keys)
    rel = get_or_create_test_relevador()
    label = relevador_etiqueta_catalogo(rel.nombre)
    assert any(i["nombre"] == label for i in items)
