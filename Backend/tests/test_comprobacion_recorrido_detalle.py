"""Presenter ``comprobacion_recorrido_detalle``: campos extendidos para UI de recorrido."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import comprobacion_recorrido_detalle
from app.models import Actuaciones, Comprobacion, Domicilio, IniciadorRuta, JuzgadoCatalogo, Oficio, OrdenTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion_con_comprobacion() -> tuple[Actuaciones, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="det recorrido test")
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
    return act, comp


def test_comprobacion_recorrido_detalle_incluye_tipo_actuacion_y_origen_iniciador(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_con_comprobacion()
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert "tipo_actuacion" in d["resultado_final"]
        assert "iniciador" in d["origen"]
        assert d["origen"]["iniciador"] is None or isinstance(d["origen"]["iniciador"], dict)
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_origen_iniciador_excluye_reinspeccion_oficio(app_ctx) -> None:
    """``origen.iniciador`` debe ser el origen de la actuación (p. ej. DENUNCIA), no REINSPECCION_OFICIO."""
    try:
        u = User(
            username=f"u_rec_{random.randint(0, 999999)}",
            email=f"rec_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        dom = Domicilio(calle=f"CalleRec{random.randint(0, 99999)}", numero="1")
        db.session.add(dom)
        db.session.flush()

        act, _comp = _mk_actuacion_con_comprobacion()
        actuacion_id = act.id

        ini_den = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 3, 1),
            anio=2026,
            mes=3,
            domicilio_id=dom.id,
            actuacion_id=actuacion_id,
            created_by_user_id=u.id,
        )
        ini_rein = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 4, 1),
            anio=2026,
            mes=4,
            domicilio_id=dom.id,
            actuacion_id=actuacion_id,
            created_by_user_id=u.id,
        )
        db.session.add_all([ini_den, ini_rein])
        db.session.flush()

        d = comprobacion_recorrido_detalle(act)
        assert d["origen"]["iniciador"] is not None
        assert d["origen"]["iniciador"]["tipo_iniciador"] == "DENUNCIA"
    finally:
        db.session.rollback()


def test_comprobacion_recorrido_detalle_oficio_incluye_causa_y_juzgado(app_ctx) -> None:
    try:
        act, comp = _mk_actuacion_con_comprobacion()
        jz = JuzgadoCatalogo(codigo=f"JZ{random.randint(1000, 9999)}", nombre="Juzgado Test Recorrido")
        db.session.add(jz)
        db.session.flush()
        ofi = Oficio(
            numero_oficio="OF-001",
            anio=2026,
            fecha_oficio=date(2026, 4, 1),
            causa="Causa test recorrido",
            comprobacion_id=comp.id,
            juzgado_id=jz.id,
        )
        db.session.add(ofi)
        db.session.flush()
        d = comprobacion_recorrido_detalle(act)
        assert d["oficio"] is not None
        assert d["oficio"]["causa"] == "Causa test recorrido"
        assert d["oficio"]["juzgado_id"] == jz.id
        assert d["oficio"]["juzgado_nombre"] == "Juzgado Test Recorrido"
    finally:
        db.session.rollback()
