"""MICROFIX V1.1-CRUD-ACTUACIONES.2A — checklist Inspector en PUT sin 500."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from app.database import db
from app.domains.actuaciones.attach.inspeccion import (
    aplicar_inspeccion_checklist_desde_payload,
    attach_inspeccion,
    items_acta_inspeccion_read_dtos,
)
from app.domains.actuaciones.mappers.actuacion_inspector_patch_mapper import (
    map_inspector_patch_to_canonical,
)
from app.domains.actuaciones.schemas.actuacion_inspector_patch_in import (
    ActuacionInspectorPatchIn,
)
from app.models import Actuaciones, Inspeccion

from app.domains.actuaciones.services.update_service import actualizar_actuacion

from tests.test_inspeccion_checklist import (
    _item_id,
    _unique_acta,
)
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401 — pytest fixture
from tests.test_inspeccion_checklist import items_catalogo  # noqa: F401 — pytest fixture


def _inspector_headers(user_id: int) -> dict[str, str]:
    token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _seed_inspeccion(scope_fixture, items_catalogo) -> tuple:
    d = scope_fixture
    act = db.session.get(Actuaciones, int(d["act_a"].id))
    assert act is not None
    id_hab = _item_id(items_catalogo, "TIENE_HABILITACION")
    acta = _unique_acta()
    attach_inspeccion(act, acta, crear=True)
    aplicar_inspeccion_checklist_desde_payload(
        act,
        {"items_acta_inspeccion": [{"item_id": id_hab, "valor_si_no": True}]},
    )
    db.session.commit()
    return d, act, id_hab


def test_map_inspector_patch_checklist_no_attr_error() -> None:
    patch = ActuacionInspectorPatchIn.model_validate(
        {
            "items_acta_inspeccion": [
                {"item_id": 1, "estado": "BIEN"},
                {"item_id": 6, "valor_si_no": True},
            ]
        }
    )
    payload = map_inspector_patch_to_canonical(patch)
    assert payload["items_acta_inspeccion"] == [
        {"item_id": 1, "estado": "BIEN"},
        {"item_id": 6, "valor_si_no": True},
    ]


def test_inspector_put_checklist_condiciones_200(
    client, scope_fixture, items_catalogo, app_ctx
) -> None:
    d, act, _id_hab = _seed_inspeccion(scope_fixture, items_catalogo)
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    id_salon = _item_id(items_catalogo, "TIENE_SALON")
    body = {
        "items_acta_inspeccion": [
            {"item_id": id_bano, "estado": "BIEN"},
            {"item_id": id_salon, "estado": "OBSERVADO"},
        ]
    }
    resp = client.put(f"/actuaciones/{act.id}", headers=_inspector_headers(d["user_a"].id), json=body)
    assert resp.status_code == 200, resp.get_json()


def test_inspector_put_checklist_habilitacion_200(
    client, scope_fixture, items_catalogo, app_ctx
) -> None:
    d, act, id_hab = _seed_inspeccion(scope_fixture, items_catalogo)
    body = {"items_acta_inspeccion": [{"item_id": id_hab, "valor_si_no": True}]}
    resp = client.put(f"/actuaciones/{act.id}", headers=_inspector_headers(d["user_a"].id), json=body)
    assert resp.status_code == 200, resp.get_json()


def test_inspector_put_checklist_mixto_200_y_persiste(
    client, scope_fixture, items_catalogo, app_ctx
) -> None:
    d, act, id_hab = _seed_inspeccion(scope_fixture, items_catalogo)
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    id_salon = _item_id(items_catalogo, "TIENE_SALON")
    body = {
        "items_acta_inspeccion": [
            {"item_id": id_bano, "estado": "BIEN"},
            {"item_id": id_salon, "estado": "BIEN"},
            {"item_id": id_hab, "valor_si_no": True},
        ]
    }
    resp = client.put(f"/actuaciones/{act.id}", headers=_inspector_headers(d["user_a"].id), json=body)
    assert resp.status_code == 200, resp.get_json()

    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None
    dtos = {int(r["id"]): r for r in items_acta_inspeccion_read_dtos(ins)}
    assert dtos[id_bano]["estado"] == "BIEN"
    assert dtos[id_salon]["estado"] == "BIEN"
    assert dtos[id_hab]["valor_si_no"] is True


def test_inspector_put_checklist_sin_item_id_422(client, scope_fixture, app_ctx) -> None:
    d = scope_fixture
    act = d["act_a"]
    resp = client.put(
        f"/actuaciones/{act.id}",
        headers=_inspector_headers(d["user_a"].id),
        json={"items_acta_inspeccion": [{"estado": "BIEN"}]},
    )
    assert resp.status_code == 422
    assert resp.status_code != 500


def test_inspector_put_checklist_actuacion_ajena_403(
    client, scope_fixture, items_catalogo, app_ctx
) -> None:
    d, act, id_hab = _seed_inspeccion(scope_fixture, items_catalogo)
    body = {"items_acta_inspeccion": [{"item_id": id_hab, "valor_si_no": True}]}
    resp = client.put(f"/actuaciones/{act.id}", headers=_inspector_headers(d["user_b"].id), json=body)
    assert resp.status_code == 403


def test_admin_update_checklist_mixto_200(scope_fixture, items_catalogo, app_ctx) -> None:
    """Regresión Admin/Usuario: servicio de update con checklist tipado (no ruta Inspector)."""
    d, act, id_hab = _seed_inspeccion(scope_fixture, items_catalogo)
    id_bano = _item_id(items_catalogo, "TIENE_BANO")
    actualizar_actuacion(
        int(act.id),
        {
            "items_acta_inspeccion": [
                {"item_id": id_bano, "estado": "BIEN"},
                {"item_id": id_hab, "valor_si_no": True},
            ]
        },
    )
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None
    dtos = {int(r["id"]): r for r in items_acta_inspeccion_read_dtos(ins)}
    assert dtos[id_bano]["estado"] == "BIEN"
    assert dtos[id_hab]["valor_si_no"] is True
