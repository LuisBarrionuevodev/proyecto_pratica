"""Política de vinculación EO desde actuación (canal grilla)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.establecimientos.services.vincular_establecimiento_operativo_actuacion_service import (
    try_vincular_establecimiento_operativo_desde_actuacion,
)
from app.models import Actuaciones, Contribuyente, Domicilio, EstablecimientoOperativo, OrdenTrabajo, Rubro, User


def _unique(prefix: str) -> str:
    return f"{prefix}_{random.randint(0, 999999)}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=_unique("u_eo"),
        email=f"{_unique('m')}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ot() -> OrdenTrabajo:
    ot = OrdenTrabajo(numero_acta=f"{random.randint(0, 999999):06d}", anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    return ot


def _mk_rubro() -> Rubro:
    r = Rubro(nombre=_unique("RubroEO"))
    db.session.add(r)
    db.session.flush()
    return r


def _mk_contrib() -> Contribuyente:
    c = Contribuyente(apellido="Pérez", nombre="Juan", documento=_unique("DOC")[:11])
    db.session.add(c)
    db.session.flush()
    return c


def _mk_dom(rubro_id: int, contrib_id: int, *, calle: str = "Mitre", numero: str = "100") -> Domicilio:
    d = Domicilio(calle=calle, numero=numero, rubro_id=rubro_id, contribuyente_id=contrib_id)
    db.session.add(d)
    db.session.flush()
    return d


def test_politica_cumple_vincula_eo(app_ctx) -> None:
    u = _mk_user()
    rub = _mk_rubro()
    con = _mk_contrib()
    dom = _mk_dom(rub.id, con.id)
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    db.session.commit()

    assert act.establecimiento_operativo_id is not None
    eo = db.session.get(EstablecimientoOperativo, act.establecimiento_operativo_id)
    assert eo is not None
    assert eo.domicilio_id == dom.id


def test_sin_tipo_no_vincula(app_ctx) -> None:
    u = _mk_user()
    rub = _mk_rubro()
    con = _mk_contrib()
    dom = _mk_dom(rub.id, con.id)
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo=None,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    db.session.commit()

    assert act.establecimiento_operativo_id is None


def test_sin_rubro_no_vincula(app_ctx) -> None:
    u = _mk_user()
    con = _mk_contrib()
    dom = Domicilio(calle="Sarmiento", numero="50", rubro_id=None, contribuyente_id=con.id)
    db.session.add(dom)
    db.session.flush()
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    db.session.commit()

    assert act.establecimiento_operativo_id is None


def test_idempotente_si_ya_coincide(app_ctx) -> None:
    u = _mk_user()
    rub = _mk_rubro()
    con = _mk_contrib()
    dom = _mk_dom(rub.id, con.id)
    eo = EstablecimientoOperativo(domicilio_id=dom.id, created_by_user_id=u.id)
    db.session.add(eo)
    db.session.flush()
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        establecimiento_operativo_id=eo.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    assert act.establecimiento_operativo_id == eo.id


def test_stale_se_limpia_y_re_vincula(app_ctx) -> None:
    u = _mk_user()
    rub = _mk_rubro()
    con = _mk_contrib()
    dom_a = _mk_dom(rub.id, con.id, calle="A", numero="1")
    dom_b = _mk_dom(rub.id, con.id, calle="B", numero="2")
    eo_a = EstablecimientoOperativo(domicilio_id=dom_a.id, created_by_user_id=u.id)
    db.session.add(eo_a)
    db.session.flush()
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom_b.id,
        establecimiento_operativo_id=eo_a.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    db.session.commit()

    assert act.establecimiento_operativo_id is not None
    assert act.establecimiento_operativo_id != eo_a.id
    eo_b = db.session.get(EstablecimientoOperativo, act.establecimiento_operativo_id)
    assert eo_b is not None
    assert eo_b.domicilio_id == dom_b.id


def test_sin_domicilio_limpia_eo(app_ctx) -> None:
    u = _mk_user()
    rub = _mk_rubro()
    con = _mk_contrib()
    dom = _mk_dom(rub.id, con.id)
    eo = EstablecimientoOperativo(domicilio_id=dom.id, created_by_user_id=u.id)
    db.session.add(eo)
    db.session.flush()
    ot = _mk_ot()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=None,
        establecimiento_operativo_id=eo.id,
    )
    db.session.add(act)
    db.session.flush()

    try_vincular_establecimiento_operativo_desde_actuacion(act, created_by_user_id=u.id)
    assert act.establecimiento_operativo_id is None
