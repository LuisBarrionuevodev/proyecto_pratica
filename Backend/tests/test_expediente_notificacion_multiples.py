"""
Múltiples expedientes PRORROGA_NOTIFICACION por notificación (historial documental).
Rama COMPROBACION sin cambios: un solo expediente de envío por comprobación.
Requiere BD; rollback al final de cada test.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)
from app.models import Actuaciones, Comprobacion, Expediente, Notificacion, OrdenTrabajo


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
    noti = Notificacion(
        numero_acta=_unique_num(),
        anio=2026,
        mes=3,
    )
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


def test_notificacion_primer_expediente_ok(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        nid = noti.id
        r = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": "100001",
                "fecha_expediente": date(2026, 3, 10),
                "prorroga_dias": 2,
            },
        )
        assert r["source_type"] == "NOTIFICACION"
        assert r["expediente"].notificacion_id == nid
        assert r["expediente"].tipo_expediente == "PRORROGA_NOTIFICACION"
        count = Expediente.query.filter_by(notificacion_id=nid).count()
        assert count == 1
    finally:
        db.session.rollback()


def test_notificacion_segundo_expediente_misma_notificacion_ok(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        nid = noti.id
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": "200002",
                "fecha_expediente": date(2026, 3, 12),
                "prorroga_dias": 1,
            },
        )
        r2 = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": "300003",
                "fecha_expediente": date(2026, 4, 1),
                "prorroga_dias": 3,
            },
        )
        assert r2["expediente"].notificacion_id == nid
        rows = (
            Expediente.query.filter_by(notificacion_id=nid)
            .order_by(Expediente.id.asc())
            .all()
        )
        assert len(rows) == 2
        assert {rows[0].numero_expediente, rows[1].numero_expediente} == {"200002", "300003"}
    finally:
        db.session.rollback()


def test_comprobacion_segundo_expediente_envio_sigue_bloqueado(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_solo_comprobacion()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": "400004",
                "fecha_expediente": date(2026, 3, 20),
            },
        )
        with pytest.raises(RuntimeError, match="Ya existe un expediente de envío"):
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": "500005",
                    "fecha_expediente": date(2026, 3, 21),
                },
            )
    finally:
        db.session.rollback()
