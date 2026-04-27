"""GET/PATCH documental de comprobación: expediente de envío y bloque oficio; bloqueo por iniciador."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.models import Actuaciones, Comprobacion, Domicilio, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio, OrdenTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _user() -> User:
    u = User(
        username=f"cdoc_{_unique_num()}",
        email=f"cdoc_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _act_comp_con_exp_envio() -> tuple[Actuaciones, Comprobacion, Expediente]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="doc test")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
    )
    db.session.add(act)
    db.session.flush()
    ex = Expediente(
        numero_expediente=_unique_num()[:6],
        anio="2026",
        fecha_expediente=date(2026, 3, 20),
        tipo_expediente="ENVIO_ACTA",
        comprobacion_id=comp.id,
        oficio_id=None,
    )
    db.session.add(ex)
    db.session.flush()
    return act, comp, ex


def test_get_comprobacion_documental_ok(app, client, auth_headers):
    with app.app_context():
        try:
            act, comp, ex = _act_comp_con_exp_envio()
            db.session.commit()
            aid, cid, eid = act.id, comp.id, ex.id
        finally:
            db.session.rollback()
    resp = client.get(f"/actuaciones/{aid}/comprobacion/documental", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    j = resp.get_json()
    assert j["actuacion_id"] == aid
    assert j["comprobacion_id"] == cid
    assert j["expediente_envio"]["id"] == eid
    assert j["edicion"]["puede_editar_expediente_envio"] is True
    assert j["edicion"]["comprobacion_usada_como_iniciador"] is False
    assert isinstance(j.get("referencia_actuacion"), dict)
    assert j["referencia_actuacion"].get("comprobacion_motivo") == "doc test"
    assert isinstance(j.get("acta_comprobacion"), dict)
    assert j["acta_comprobacion"].get("motivo") == "doc test"


def test_patch_expediente_envio_ok(app, client, auth_headers):
    with app.app_context():
        try:
            act, _comp, ex = _act_comp_con_exp_envio()
            db.session.commit()
            aid, eid = act.id, ex.id
            nuevo = _unique_num()[:6]
            resp = client.patch(
                f"/actuaciones/{aid}/comprobacion/expediente-envio/{eid}",
                headers=auth_headers,
                json={"numero_expediente": nuevo, "fecha_expediente": "2026-04-02"},
            )
            assert resp.status_code == 200, resp.get_data(as_text=True)
            body = resp.get_json()
            assert body["item"]["numero_expediente"] == nuevo
            assert body["item"]["anio"] == "2026"
        finally:
            db.session.rollback()


def test_patch_expediente_envio_bloqueado_por_iniciador_comprobacion(app, client, auth_headers):
    with app.app_context():
        try:
            u = _user()
            dom = Domicilio(calle="DocBlock", numero="1")
            db.session.add(dom)
            db.session.flush()
            act, comp, ex = _act_comp_con_exp_envio()
            act.domicilio_id = dom.id
            ini = IniciadorRuta(
                tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 1),
                anio=2026,
                mes=3,
                domicilio_id=dom.id,
                comprobacion_id=comp.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.commit()
            aid, eid = act.id, ex.id
        finally:
            db.session.rollback()

    resp = client.patch(
        f"/actuaciones/{aid}/comprobacion/expediente-envio/{eid}",
        headers=auth_headers,
        json={"numero_expediente": _unique_num()[:6], "fecha_expediente": "2026-04-02"},
    )
    assert resp.status_code == 400
    detail = (resp.get_json() or {}).get("detail", "").lower()
    assert "iniciador" in detail


def test_patch_oficio_bloque_ok(app, client, auth_headers):
    with app.app_context():
        try:
            act, comp, _ex_env = _act_comp_con_exp_envio()
            jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()[:4]}", nombre=f"Juzgado doc {_unique_num()}")
            db.session.add(jz)
            db.session.flush()
            ofi_num = f"D{_unique_num()[:5]}"
            ofi = Oficio(
                numero_oficio=ofi_num,
                anio=2026,
                fecha_oficio=date(2026, 4, 1),
                causa=f"causa {_unique_num()[:5]}",
                comprobacion_id=comp.id,
                juzgado_id=jz.id,
            )
            db.session.add(ofi)
            db.session.flush()
            ex_r = Expediente(
                numero_expediente=_unique_num()[:6],
                anio="2026",
                fecha_expediente=date(2026, 4, 5),
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp.id,
                oficio_id=ofi.id,
            )
            db.session.add(ex_r)
            db.session.commit()
            aid, oid, jz_id = act.id, ofi.id, jz.id
            nuevo_ofi = f"D{_unique_num()[:5]}"
            nuevo_ex = _unique_num()[:6]
        finally:
            db.session.rollback()

    resp = client.patch(
        f"/actuaciones/{aid}/comprobacion/oficios/{oid}",
        headers=auth_headers,
        json={
            "numero_oficio": nuevo_ofi,
            "fecha_oficio": "2026-05-01",
            "juzgado_id": jz_id,
            "causa": f"causa patch {_unique_num()[:5]}",
            "numero_expediente_respuesta": nuevo_ex,
            "fecha_expediente_respuesta": "2026-05-02",
        },
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    j = resp.get_json()
    assert j["oficio_item"]["numero_oficio"] == nuevo_ofi
    assert j["expediente_respuesta_item"]["numero_expediente"] == nuevo_ex
