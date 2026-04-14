"""
Canal Cargar actuación: no editar notificación/comprobación si ya tienen expediente asociado.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_actas_edit_guard import (
    assert_canal_actas_permite_payload_notificacion_comprobacion,
)
from app.models import Actuaciones, Comprobacion, Expediente, Notificacion, OrdenTrabajo
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion_solo_notificacion() -> tuple[Actuaciones, Notificacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
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
    )
    db.session.add(act)
    db.session.flush()
    return act, noti


def _mk_actuacion_solo_comprobacion() -> tuple[Actuaciones, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="test comp")
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


def test_notificacion_sin_expediente_permite_payload_con_notificacion(app_ctx) -> None:
    try:
        act, _noti = _mk_actuacion_solo_notificacion()
        db.session.commit()
        assert_canal_actas_permite_payload_notificacion_comprobacion(
            act, {"notificacion": {"acta_num": "123456", "motivos": ["m"]}}
        )
    finally:
        db.session.rollback()


def test_notificacion_con_expediente_bloquea_payload_con_notificacion(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        ex = Expediente(
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 3, 10),
            tipo_expediente="PRORROGA_NOTIFICACION",
            notificacion_id=noti.id,
            comprobacion_id=None,
            oficio_id=None,
        )
        db.session.add(ex)
        db.session.commit()
        with pytest.raises(ValueError, match="notificación ya tiene expediente"):
            assert_canal_actas_permite_payload_notificacion_comprobacion(
                act, {"notificacion": {"acta_num": "123456", "motivos": ["m"]}}
            )
    finally:
        db.session.rollback()


def test_comprobacion_sin_expediente_permite_payload_con_comprobacion(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_solo_comprobacion()
        db.session.commit()
        assert_canal_actas_permite_payload_notificacion_comprobacion(
            act, {"comprobacion": {"acta_num": "123456", "motivo": "un motivo"}}
        )
    finally:
        db.session.rollback()


def test_comprobacion_con_expediente_envio_bloquea_payload_con_comprobacion(app_ctx) -> None:
    try:
        act, comp = _mk_actuacion_solo_comprobacion()
        ex = Expediente(
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 3, 12),
            tipo_expediente="ENVIO_ACTA",
            comprobacion_id=comp.id,
            notificacion_id=None,
            oficio_id=None,
        )
        db.session.add(ex)
        db.session.commit()
        with pytest.raises(ValueError, match="comprobación ya tiene expediente"):
            assert_canal_actas_permite_payload_notificacion_comprobacion(
                act, {"comprobacion": {"acta_num": "123456", "motivo": "un motivo"}}
            )
    finally:
        db.session.rollback()
