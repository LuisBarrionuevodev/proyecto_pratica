"""P0 V1.1-ACT-SEGUIMIENTO.2 — no validar seguimiento no modificado en PUT Gestión."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.database import db
from app.models import Actuaciones
from app.models.solicitud_carnet_manipulador import SolicitudCarnetManipulador
from tests.test_acta_seguimiento_gestion_1e import _put_http
from tests.test_acta_seguimiento_gestion_v1_1b import (
    _cerrar_relevamiento_sin_carnet,
    _put_gestion,
)
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401


def _unlink_contribuyente(act: Actuaciones) -> None:
    """Simula actuación histórica/parcialmente vinculada: domicilio sin contribuyente_id."""
    db.session.refresh(act)
    dom = act.domicilio
    assert dom is not None
    dom.contribuyente_id = None
    db.session.flush()
    db.session.commit()
    db.session.refresh(act)
    assert act.domicilio is not None
    assert act.domicilio.contribuyente_id is None


def test_put_ajeno_con_domicilio_sin_contribuyente_200(app, client, app_ctx) -> None:
    """Seguimiento existente/No y edición ajena no exige contribuyente."""
    act, u = _cerrar_relevamiento_sin_carnet()
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is False
    _unlink_contribuyente(act)

    resp = _put_http(client, act, u.id)
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    errors = (body or {}).get("errors") if isinstance(body, dict) else None
    assert not errors or "doc_nro" not in errors
    assert not errors or "solicita_carnet_manipulador" not in errors


def test_put_explicito_carnet_sin_contribuyente_422_en_seguimiento(
    app, client, app_ctx
) -> None:
    """Cambio explícito de carnet sin contribuyente_id: 422 en seguimiento, no en doc_nro."""
    act, u = _cerrar_relevamiento_sin_carnet()
    _unlink_contribuyente(act)

    resp = _put_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet="381 222-3333",
    )
    assert resp.status_code == 422, resp.get_json()
    errors = resp.get_json()["errors"]
    assert "solicita_carnet_manipulador" in errors
    assert "doc_nro" not in errors
    assert "contribuyente" in errors["solicita_carnet_manipulador"].lower()


def test_put_explicito_carnet_sin_contribuyente_service_no_usa_doc_nro(app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    _unlink_contribuyente(act)

    with pytest.raises(ValidationError) as exc:
        _put_gestion(
            act,
            u,
            solicita_carnet_manipulador=True,
            telefono_contacto_solicitud_carnet="381 222-3333",
        )
    locs = [err.get("loc", ()) for err in exc.value.errors()]
    assert any(loc and loc[0] == "solicita_carnet_manipulador" for loc in locs)
    assert not any(loc and loc[0] == "doc_nro" for loc in locs)


def test_put_explicito_carnet_vinculado_persiste(app, client, app_ctx) -> None:
    """Domicilio con contribuyente_id: cambio explícito de carnet sigue persistiendo."""
    act, u = _cerrar_relevamiento_sin_carnet()
    assert act.domicilio is not None
    assert act.domicilio.contribuyente_id is not None

    tel = "381 888-0001"
    resp = _put_http(
        client,
        act,
        u.id,
        solicita_carnet_manipulador=True,
        telefono_contacto_solicitud_carnet=tel,
    )
    assert resp.status_code == 200, resp.get_json()
    db.session.expire_all()
    sol = SolicitudCarnetManipulador.query.filter_by(inspeccion_id=act.inspeccion.id).one()
    assert sol.solicita_carnet is True
    assert sol.telefono_contacto == tel
