"""PATCH notificación: expediente de prórroga (número, fecha, plazo otorgado) y reglas de iniciador."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    evaluar_notificacion_edicion_permisos,
    update_notificacion_prorroga_expediente,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.models import Actuaciones, Domicilio, Expediente, IniciadorRuta, Notificacion, OrdenTrabajo, User
from sqlalchemy import inspect, text


@pytest.fixture(autouse=True)
def _ensure_expediente_prorroga_dias_otorgados_column(app):
    """DDL idempotente si la migración Alembic aún no se aplicó en la BD de tests."""
    with app.app_context():
        from app.database import db

        try:
            cols = {c["name"] for c in inspect(db.engine).get_columns("expediente")}
        except Exception:
            return
        if "prorroga_dias_otorgados" in cols:
            return
        dialect = db.engine.dialect.name
        if dialect == "mysql":
            db.session.execute(text("ALTER TABLE expediente ADD COLUMN prorroga_dias_otorgados INT NULL"))
        else:
            db.session.execute(
                text("ALTER TABLE expediente ADD COLUMN prorroga_dias_otorgados INTEGER NULL")
            )
        db.session.commit()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _user() -> User:
    u = User(
        username=f"edn_{_unique_num()}",
        email=f"edn_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _act_noti_con_dom() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="EditPlazo", numero="1")
    db.session.add(dom)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    db.session.add(noti)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_patch_expediente_prorroga_ok_recuenta_plazo(app, client, auth_headers):
    with app.app_context():
        try:
            act = _act_noti_con_dom()
            db.session.commit()
            aid = act.id
            complete_expediente_from_actuacion(
                aid,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 5),
                    "prorroga_dias": 1,
                },
            )
            act2 = Actuaciones.query.get(aid)
            assert act2 is not None
            ex_row = Expediente.query.filter_by(notificacion_id=act2.notificacion_id).first()
            eid = ex_row.id

            nuevo_num = _unique_num()
            resp2 = client.patch(
                f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}",
                headers=auth_headers,
                json={
                    "numero_expediente": nuevo_num,
                    "fecha_expediente": "2026-03-08",
                    "plazo_otorgado": 4,
                },
            )
            assert resp2.status_code == 200, resp2.get_data(as_text=True)
            j = resp2.get_json()
            assert j["item"]["numero_expediente"] == nuevo_num
            assert j["item"]["plazo_otorgado"] == 4
            assert j["plazo_notificacion"]["prorroga_total_dias"] == 4

            noti = db.session.get(Notificacion, int(act2.notificacion_id))
            assert noti is not None
            assert int(noti.prorroga_dias or 0) == 4
        finally:
            db.session.rollback()


def test_patch_expediente_bloqueado_si_notificacion_usada_como_iniciador(app, client, auth_headers):
    with app.app_context():
        try:
            u = _user()
            act = _act_noti_con_dom()
            db.session.flush()
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 5),
                    "prorroga_dias": 1,
                },
            )
            ex_row = Expediente.query.filter_by(notificacion_id=act.notificacion_id).first()
            eid = ex_row.id

            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_NOTIFICACION",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                notificacion_id=act.notificacion_id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.commit()
            aid = act.id

            resp = client.patch(
                f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}",
                headers=auth_headers,
                json={
                    "numero_expediente": _unique_num(),
                    "fecha_expediente": "2026-03-08",
                    "plazo_otorgado": 0,
                },
            )
            assert resp.status_code == 400
            detail = (resp.get_json() or {}).get("detail", "").lower()
            assert "iniciador" in detail or "usada" in detail
        finally:
            db.session.rollback()


def test_evaluar_permisos_bloqueo_si_iniciador_vinculado_a_notificacion(app) -> None:
    with app.app_context():
        try:
            u = _user()
            act = _act_noti_con_dom()
            db.session.flush()
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_NOTIFICACION",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                notificacion_id=act.notificacion_id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.flush()
            per = evaluar_notificacion_edicion_permisos(act)
            assert per["puede_editar_expediente_prorroga"] is False
            assert per.get("puede_eliminar_expediente_prorroga") is False
            assert per.get("notificacion_usada_como_iniciador") is True
        finally:
            db.session.rollback()


def test_delete_expediente_prorroga_ok_recuenta_plazo(app, client, auth_headers):
    with app.app_context():
        try:
            act = _act_noti_con_dom()
            db.session.commit()
            aid = act.id
            complete_expediente_from_actuacion(
                aid,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 5),
                    "prorroga_dias": 3,
                },
            )
            act2 = Actuaciones.query.get(aid)
            ex_row = Expediente.query.filter_by(notificacion_id=act2.notificacion_id).first()
            eid = ex_row.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}", headers=auth_headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    j = resp.get_json()
    assert j["ok"] is True
    assert j["plazo_notificacion"]["prorroga_total_dias"] == 0

    with app.app_context():
        ex_db = db.session.get(Expediente, eid)
        assert ex_db is not None
        assert ex_db.deleted_at is not None


def test_delete_expediente_prorroga_bloqueado_si_iniciador(app, client, auth_headers):
    with app.app_context():
        try:
            u = _user()
            act = _act_noti_con_dom()
            db.session.flush()
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 5),
                    "prorroga_dias": 1,
                },
            )
            ex_row = Expediente.query.filter_by(notificacion_id=act.notificacion_id).first()
            eid = ex_row.id
            ini = IniciadorRuta(
                tipo_iniciador="REINSPECCION_NOTIFICACION",
                estado_iniciador="PENDIENTE",
                fecha_origen=date(2026, 3, 20),
                anio=2026,
                mes=3,
                domicilio_id=act.domicilio_id,
                actuacion_id=act.id,
                notificacion_id=act.notificacion_id,
                created_by_user_id=u.id,
            )
            db.session.add(ini)
            db.session.commit()
            aid = act.id
        finally:
            db.session.rollback()

    resp = client.delete(f"/actuaciones/{aid}/notificacion/expedientes-prorroga/{eid}", headers=auth_headers)
    assert resp.status_code == 400


def test_update_expediente_service_value_error_sin_fecha_notificacion(app) -> None:
    with app.app_context():
        try:
            act = _act_noti_con_dom()
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 5),
                    "prorroga_dias": 1,
                },
            )
            ex_row = Expediente.query.filter_by(notificacion_id=act.notificacion_id).first()
            noti = db.session.get(Notificacion, int(act.notificacion_id))
            noti.fecha_notificacion = None
            db.session.add(noti)
            db.session.flush()
            with pytest.raises(ValueError, match="fecha_notificacion"):
                update_notificacion_prorroga_expediente(
                    act.id,
                    ex_row.id,
                    numero_expediente=ex_row.numero_expediente,
                    fecha_expediente=date(2026, 3, 8),
                    plazo_otorgado=0,
                )
        finally:
            db.session.rollback()
