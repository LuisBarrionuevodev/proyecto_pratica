"""HOTFIX V1.1-ACT-EDIT.1C — editar domicilio en inspecciones normales."""

from __future__ import annotations

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    MSG_REINSPECCION,
    puede_editar_domicilio_actuacion,
)
from app.models import Actuaciones, Domicilio
from tests.test_acta_identidad_gestion_1 import _contribuyente_id, _put_gestion_http
from tests.test_acta_seguimiento_gestion_v1_1b import (
    _cerrar_denuncia_sin_carnet,
    _cerrar_relevamiento_sin_carnet,
)
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item
from tests.test_inspector_scope_v1_1_2 import scope_fixture  # noqa: F401


def test_relevamiento_permite_editar_domicilio(app_ctx) -> None:
    act, _u = _cerrar_relevamiento_sin_carnet()
    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None
    row = actuacion_to_grid_row(act)
    assert row["can_edit_domicilio"] is True


def test_denuncia_permite_editar_domicilio(app_ctx) -> None:
    act, _u = _cerrar_denuncia_sin_carnet()
    puede, motivo = puede_editar_domicilio_actuacion(act)
    assert puede is True
    assert motivo is None
    row = actuacion_to_grid_row(act)
    assert row["can_edit_domicilio"] is True
    assert row.get("domicilio_edit_blocked_reason") in (None, "")


def test_reinspeccion_real_bloquea_domicilio(app_ctx) -> None:
    _item, act_work, _ini, _u, _noti = _mk_reinspeccion_notificacion_item()
    puede, motivo = puede_editar_domicilio_actuacion(act_work)
    assert puede is False
    assert motivo == MSG_REINSPECCION


def test_put_relevamiento_cambia_calle_sin_identidad_conserva_contribuyente(
    app, client, app_ctx
) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None
    acta_num = act.inspeccion.numero_acta if act.inspeccion else None

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        calle="Catamarca 1C",
        numero="250",
        numero_tipo="NUMERO",
    )
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid
    db.session.expire_all()
    act_db = Actuaciones.query.get(int(act.id))
    assert act_db is not None and act_db.domicilio is not None
    assert act_db.domicilio.calle == "Catamarca 1C"
    assert act_db.domicilio.numero == "250"
    if acta_num:
        assert act_db.inspeccion is not None
        assert act_db.inspeccion.numero_acta == acta_num


def test_put_denuncia_cambia_calle_sin_identidad_conserva_contribuyente(
    app, client, app_ctx
) -> None:
    act, u = _cerrar_denuncia_sin_carnet()
    cid = _contribuyente_id(act)
    assert cid is not None

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        calle="Belgrano 1C",
        numero="88",
        numero_tipo="ESQUINA",
    )
    assert resp.status_code == 200, resp.get_json()
    assert _contribuyente_id(act) == cid
    db.session.expire_all()
    act_db = Actuaciones.query.get(int(act.id))
    assert act_db is not None and act_db.domicilio is not None
    assert act_db.domicilio.calle == "Belgrano 1C"
    assert act_db.domicilio.numero == "88"


def test_put_domicilio_sin_contribuyente_real_no_guarda(app, client, app_ctx) -> None:
    act, u = _cerrar_relevamiento_sin_carnet()
    db.session.refresh(act)
    assert act.domicilio is not None
    act.domicilio.contribuyente_id = None
    db.session.flush()
    db.session.commit()
    assert _contribuyente_id(act) is None
    calle_prev = act.domicilio.calle

    resp = _put_gestion_http(
        client,
        act,
        u.id,
        calle="Nueva Sin Titular",
        numero="9",
        numero_tipo="NUMERO",
    )
    assert resp.status_code == 400, resp.get_json()
    body = resp.get_json() or {}
    assert str(body.get("detail", "")) == "Si cargás domicilio, debés cargar contribuyente."
    db.session.expire_all()
    dom = Domicilio.query.get(int(act.domicilio_id))
    assert dom is not None
    assert dom.calle == calle_prev
