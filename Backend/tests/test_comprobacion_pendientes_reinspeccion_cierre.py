"""Pendiente reinspección comprobación: excluir trámites cumplidos."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.models import Actuaciones, IniciadorRuta, User

from tests.test_comprobacion_pendientes_reinspeccion_bandeja import (
    _mk_circuito_completo,
    _mk_user,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_oficio_cumplido_no_aparece_en_pendientes(app_ctx) -> None:
    act_id, _nof, _jz = _mk_circuito_completo()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    u = _mk_user()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="CUMPLIDO",
        fecha_origen=date(2026, 3, 20),
        anio=2026,
        mes=3,
        domicilio_id=act.domicilio_id,
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.commit()

    filters = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
    filas = list_pendientes_reinspeccion_oficio_filas(filters)
    act_ids = {a.id for a, _o, _i in filas}
    assert act_id not in act_ids


def test_oficio_pendiente_reencolado_aparece(app_ctx) -> None:
    act_id, _nof, _jz = _mk_circuito_completo()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    u = _mk_user()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 3, 20),
        anio=2026,
        mes=3,
        domicilio_id=act.domicilio_id,
        actuacion_id=act.id,
        created_by_user_id=u.id,
        prioridad=5,
    )
    db.session.add(ini)
    db.session.commit()

    filters = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
    filas = list_pendientes_reinspeccion_oficio_filas(filters)
    assert any(a.id == act_id for a, _o, i in filas if i is not None)
