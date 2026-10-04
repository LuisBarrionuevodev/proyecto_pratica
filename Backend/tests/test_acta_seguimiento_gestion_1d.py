"""HOTFIX V1.1-ACTA-SEGUIMIENTO.1D — contexto domicilio en detalle autorizado."""

from __future__ import annotations

from app.database import db
from tests.test_acta_seguimiento_gestion_1c import _auth_headers, _put_gestion
from tests.test_acta_seguimiento_gestion_v1_1b import _cerrar_relevamiento_sin_carnet


def test_get_gestion_incluye_domicilio_rubro_contribuyente(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _put_gestion(
        act,
        u,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 000-1111",
    )
    db.session.expire_all()
    act_id = int(act.id)
    headers = _auth_headers(u.id)

    det = client.get(f"/actuaciones/{act_id}/gestion", headers=headers)
    assert det.status_code == 200
    body = det.get_json()
    assert body["ui_policy"]["puede_editar_seguimiento"] is True
    assert "domicilio" in body
    assert "rubro" in body
    assert "contribuyente" in body
    assert body["domicilio"]["calle"] is not None
    assert body["contribuyente"]["apellido"] is not None or body["contribuyente"]["nombre"] is not None

    lst = client.get(
        f"/actuaciones?actuacion_id={act_id}&desde=2026-01-01&hasta=2026-12-31",
        headers=headers,
    )
    assert lst.status_code == 200
    row = lst.get_json()["items"][0]
    assert not isinstance(row.get("domicilio"), dict)
    assert row.get("telefono_contacto_solicitud_carnet") is None
