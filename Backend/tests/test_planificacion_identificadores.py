"""STAB-10c — identificadores en presenter de planificación."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    iniciador_pendiente_present,
    iniciador_pendiente_to_map_pin,
    iniciador_pendiente_to_row,
)
from app.models import Comprobacion, Denuncia, Domicilio, IniciadorRuta, Notificacion, Oficio, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"id10c_{_unique_num()}",
        email=f"id10c_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def test_urgente_oficio_incluye_numero_oficio_y_comprobacion(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"IdOfi{_unique_num()}", numero="1")
        db.session.add(dom)
        db.session.flush()
        ncomp = _unique_num()
        comp = Comprobacion(numero_acta=ncomp, anio=2026, mes=6)
        db.session.add(comp)
        db.session.flush()
        nof = f"OF{_unique_num()[:5]}"
        ofi = Oficio(numero_oficio=nof, anio=2026, comprobacion_id=comp.id)
        db.session.add(ofi)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=3,
            oficio_id=ofi.id,
            comprobacion_id=comp.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        ident = row["identificadores"]
        assert ident["numero_oficio"] == nof
        assert ident["anio_oficio"] == 2026
        assert ident["numero_comprobacion"] == ncomp
        assert ident["anio_comprobacion"] == 2026
    finally:
        db.session.rollback()


def test_reinspeccion_notificacion_incluye_numero_notificacion(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"IdNot{_unique_num()}", numero="2")
        db.session.add(dom)
        db.session.flush()
        nacta = _unique_num()
        noti = Notificacion(numero_acta=nacta, anio=2026, mes=6)
        db.session.add(noti)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=3,
            notificacion_id=noti.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ident = iniciador_pendiente_to_row(ini)["identificadores"]
        assert ident["numero_notificacion"] == nacta
        assert ident["anio_notificacion"] == 2026
    finally:
        db.session.rollback()


def test_denuncia_no_rompe_sin_numero_formal(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"IdDen{_unique_num()}", numero="3")
        db.session.add(dom)
        db.session.flush()
        den = Denuncia(
            fecha=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            motivo="test",
            created_by_user_id=u.id,
        )
        db.session.add(den)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=3,
            denuncia_id=den.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ident = iniciador_pendiente_to_row(ini)["identificadores"]
        assert ident["numero_denuncia"] is None
        assert ident["numero_oficio"] is None
    finally:
        db.session.rollback()


def test_m4_minimal_incluye_identificadores_y_mantiene_recorte(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"IdMin{_unique_num()}", numero="4")
        db.session.add(dom)
        db.session.flush()
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(comp)
        db.session.flush()
        ofi = Oficio(numero_oficio=f"OF{_unique_num()[:4]}", anio=2026, comprobacion_id=comp.id)
        db.session.add(ofi)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=4,
            oficio_id=ofi.id,
            comprobacion_id=comp.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        full = iniciador_pendiente_to_row(ini)
        minimal = iniciador_pendiente_to_map_pin(ini)
        assert "turno_sugerido" not in minimal
        assert "identificadores" in minimal
        assert minimal["identificadores"]["numero_oficio"] == full["identificadores"]["numero_oficio"]
        assert iniciador_pendiente_present(ini, fields="minimal") == minimal
    finally:
        db.session.rollback()
