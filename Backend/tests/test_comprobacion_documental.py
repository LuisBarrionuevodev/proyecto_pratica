"""GET/PATCH documental de comprobación: expediente de envío y bloque oficio; bloqueo por iniciador."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.models import Actuaciones, Comprobacion, Domicilio, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio, OrdenTrabajo, RutaItem, RutaTrabajo, User


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
    assert j["edicion"]["puede_eliminar_expediente_envio"] is True
    assert j["edicion"]["puede_eliminar_bloque_oficio"] is False
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


def test_delete_expediente_envio_ok(app, client, auth_headers):
    with app.app_context():
        try:
            act, _comp, ex = _act_comp_con_exp_envio()
            db.session.commit()
            aid, eid = act.id, ex.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/expediente-envio/{eid}", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert (resp.get_json() or {}).get("ok") is True

    with app.app_context():
        ex_db = db.session.get(Expediente, eid)
        assert ex_db is not None
        assert ex_db.deleted_at is not None


def test_delete_expediente_envio_bloqueado_si_hay_oficio(app, client, auth_headers):
    with app.app_context():
        try:
            act, comp, ex = _act_comp_con_exp_envio()
            jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()[:4]}", nombre=f"Juzgado del {_unique_num()}")
            db.session.add(jz)
            db.session.flush()
            ofi = Oficio(
                numero_oficio=f"O{_unique_num()[:5]}",
                anio=2026,
                fecha_oficio=date(2026, 4, 1),
                causa=f"c{_unique_num()[:5]}",
                comprobacion_id=comp.id,
                juzgado_id=jz.id,
            )
            db.session.add(ofi)
            db.session.flush()
            ex_r = Expediente(
                numero_expediente=_unique_num()[:6],
                anio="2026",
                fecha_expediente=date(2026, 4, 2),
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp.id,
                oficio_id=ofi.id,
            )
            db.session.add(ex_r)
            db.session.commit()
            aid, eid = act.id, ex.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/expediente-envio/{eid}", headers=auth_headers)
    assert resp.status_code == 400
    assert "oficio" in (resp.get_json() or {}).get("detail", "").lower()


def test_delete_expediente_envio_bloqueado_por_iniciador(app, client, auth_headers):
    with app.app_context():
        try:
            u = _user()
            dom = Domicilio(calle="DocDel", numero="1")
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

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/expediente-envio/{eid}", headers=auth_headers)
    assert resp.status_code == 400


def test_delete_oficio_bloque_ok(app, client, auth_headers):
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
            aid, oid, rid = act.id, ofi.id, ex_r.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/oficios/{oid}", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)

    with app.app_context():
        o_db = db.session.get(Oficio, oid)
        e_db = db.session.get(Expediente, rid)
        assert o_db is not None and o_db.deleted_at is not None
        assert e_db is not None and e_db.deleted_at is not None


def test_delete_oficio_bloque_soft_delete_iniciador_pendiente(app, client, auth_headers):
    """PR11.3: eliminar oficio no usado debe anular el iniciador asociado."""
    with app.app_context():
        try:
            u = _user()
            dom = Domicilio(calle="DocDelIni", numero="3")
            db.session.add(dom)
            db.session.flush()
            act, comp, _ex_env = _act_comp_con_exp_envio()
            act.domicilio_id = dom.id
            jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()[:4]}", nombre=f"Jz {_unique_num()}")
            db.session.add(jz)
            db.session.flush()
            ofi = Oficio(
                numero_oficio=f"Y{_unique_num()[:5]}",
                anio=2026,
                fecha_oficio=date(2026, 4, 1),
                causa=f"c{_unique_num()[:5]}",
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
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 1),
                anio=2026,
                mes=3,
                domicilio_id=dom.id,
                comprobacion_id=comp.id,
                oficio_id=ofi.id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.commit()
            aid, oid, ini_id = act.id, ofi.id, ini.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/oficios/{oid}", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)

    with app.app_context():
        ini_db = db.session.get(IniciadorRuta, ini_id)
        assert ini_db is not None
        assert ini_db.deleted_at is not None
        assert ini_db.estado_iniciador == "ANULADO"


def test_delete_oficio_bloque_bloqueado_por_ruta_publicada(app, client, auth_headers):
    """PR11.3: oficio usado en ruta publicada devuelve 409."""
    with app.app_context():
        try:
            u = _user()
            dom = Domicilio(calle="DocDelOfi", numero="2")
            db.session.add(dom)
            db.session.flush()
            act, comp, _ex_env = _act_comp_con_exp_envio()
            act.domicilio_id = dom.id
            jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()[:4]}", nombre=f"Jz {_unique_num()}")
            db.session.add(jz)
            db.session.flush()
            ofi = Oficio(
                numero_oficio=f"X{_unique_num()[:5]}",
                anio=2026,
                fecha_oficio=date(2026, 4, 1),
                causa=f"c{_unique_num()[:5]}",
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
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 1),
                anio=2026,
                mes=3,
                domicilio_id=dom.id,
                comprobacion_id=comp.id,
                oficio_id=ofi.id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            ruta = RutaTrabajo(
                fecha=date(2026, 6, 15),
                turno="TARDE",
                estado_ruta="PUBLICADA",
                created_by_user_id=u.id,
                numero=random.randint(2, 32000),
            )
            db.session.add(ruta)
            db.session.flush()
            db.session.add(
                RutaItem(
                    ruta_trabajo_id=ruta.id,
                    iniciador_ruta_id=ini.id,
                    orden_trabajo_id=act.orden_trabajo_id,
                    estado_ruta_item="PENDIENTE_ASIGNACION",
                    actuacion_id=act.id,
                    created_by_user_id=u.id,
                )
            )
            db.session.commit()
            aid, oid = act.id, ofi.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/oficios/{oid}", headers=auth_headers)
    assert resp.status_code == 409
    detail = (resp.get_json() or {}).get("detail", "").lower()
    assert "ruta" in detail or "utilizado" in detail


def test_delete_oficio_bloque_bloqueado_por_iniciador_cumplido(app, client, auth_headers):
    """PR11.3: oficio con iniciador cumplido devuelve 409."""
    with app.app_context():
        try:
            u = _user()
            dom = Domicilio(calle="DocDelCum", numero="4")
            db.session.add(dom)
            db.session.flush()
            act, comp, _ex_env = _act_comp_con_exp_envio()
            act.domicilio_id = dom.id
            jz = JuzgadoCatalogo(codigo=f"JZ{_unique_num()[:4]}", nombre=f"Jz {_unique_num()}")
            db.session.add(jz)
            db.session.flush()
            ofi = Oficio(
                numero_oficio=f"Z{_unique_num()[:5]}",
                anio=2026,
                fecha_oficio=date(2026, 4, 1),
                causa=f"c{_unique_num()[:5]}",
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
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_OFICIO",
                estado_iniciador="CUMPLIDO",
                fecha_origen=date(2026, 3, 1),
                anio=2026,
                mes=3,
                domicilio_id=dom.id,
                comprobacion_id=comp.id,
                oficio_id=ofi.id,
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.commit()
            aid, oid = act.id, ofi.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/comprobacion/oficios/{oid}", headers=auth_headers)
    assert resp.status_code == 409
