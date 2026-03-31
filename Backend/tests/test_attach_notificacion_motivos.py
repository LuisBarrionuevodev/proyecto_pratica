"""
Reglas de motivos en attach_notificacion (acta + al menos un motivo).
Requiere BD; rollback al final de cada test.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.models import Actuaciones, Motivo, Notificacion, OrdenTrabajo


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_attach_notificacion_acta_sin_motivos_falla(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        with pytest.raises(ValueError, match="La notificación requiere al menos un motivo"):
            attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": []})
    finally:
        db.session.rollback()


def test_attach_notificacion_acta_con_un_motivo_ok(app_ctx) -> None:
    try:
        m = Motivo.query.first()
        if m is None:
            m = Motivo(nombre=f"mt_{_unique_ot_num()}")
            db.session.add(m)
            db.session.flush()

        act = _mk_actuacion()
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()
        assert act.notificacion_id is not None
        n = db.session.get(Notificacion, act.notificacion_id)
        assert n is not None
        assert len(n.motivos) >= 1
    finally:
        db.session.rollback()
