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
    AMBIGUO_EXPEDIENTE_SOURCE,
    complete_expediente_from_actuacion,
    infer_source_type_from_actuacion,
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


def _mk_actuacion_mixta() -> tuple[Actuaciones, Notificacion, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    db.session.add(noti)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="test mix comp")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 2),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        comprobacion_id=comp.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti, comp


def test_infer_mixta_es_ambigua(app_ctx) -> None:
    act, _n, _c = _mk_actuacion_mixta()
    assert infer_source_type_from_actuacion(act) == AMBIGUO_EXPEDIENTE_SOURCE


def test_solo_notificacion_source_type_erroneo_rechaza(app_ctx) -> None:
    try:
        act, _noti = _mk_actuacion_solo_notificacion()
        with pytest.raises(RuntimeError, match="source_type no coincide"):
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 10),
                    "prorroga_dias": 0,
                    "source_type": "COMPROBACION",
                },
            )
    finally:
        db.session.rollback()


def test_mixta_sin_source_type_rechaza(app_ctx) -> None:
    try:
        act, _n, _c = _mk_actuacion_mixta()
        with pytest.raises(ValueError, match="Indicá source_type"):
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 10),
                    "prorroga_dias": 0,
                },
            )
    finally:
        db.session.rollback()


def test_mixta_canal_notificacion_crea_prorroga(app_ctx) -> None:
    try:
        act, noti, _comp = _mk_actuacion_mixta()
        nid = noti.id
        ex_num = _unique_num()
        r = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex_num,
                "fecha_expediente": date(2026, 3, 10),
                "prorroga_dias": 1,
                "source_type": "NOTIFICACION",
            },
        )
        assert r["source_type"] == "NOTIFICACION"
        assert r["expediente"].notificacion_id == nid
        assert r["expediente"].comprobacion_id is None
        assert r["expediente"].tipo_expediente == "PRORROGA_NOTIFICACION"
    finally:
        db.session.rollback()


def test_mixta_canal_comprobacion_crea_envio(app_ctx) -> None:
    try:
        act, _noti, comp = _mk_actuacion_mixta()
        cid = comp.id
        r = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 20),
                "source_type": "COMPROBACION",
            },
        )
        assert r["source_type"] == "COMPROBACION"
        assert r["expediente"].comprobacion_id == cid
        assert r["expediente"].notificacion_id is None
        assert r["expediente"].tipo_expediente == "ENVIO_ACTA"
    finally:
        db.session.rollback()


def test_mixta_ambos_canales_en_orden(app_ctx) -> None:
    """Plazo por notificación y envío por comprobación en la misma actuación."""
    try:
        act, noti, comp = _mk_actuacion_mixta()
        ex_n = _unique_num()
        ex_c = _unique_num()
        r1 = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex_n,
                "fecha_expediente": date(2026, 3, 11),
                "prorroga_dias": 0,
                "source_type": "NOTIFICACION",
            },
        )
        r2 = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex_c,
                "fecha_expediente": date(2026, 3, 22),
                "source_type": "COMPROBACION",
            },
        )
        assert r1["expediente"].notificacion_id == noti.id
        assert r2["expediente"].comprobacion_id == comp.id
        assert Expediente.query.filter_by(notificacion_id=noti.id).count() >= 1
        assert Expediente.query.filter_by(comprobacion_id=comp.id, oficio_id=None).count() == 1
    finally:
        db.session.rollback()


def test_notificacion_primer_expediente_ok(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        nid = noti.id
        ex_num = _unique_num()
        r = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex_num,
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
        ex1 = _unique_num()
        ex2 = _unique_num()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex1,
                "fecha_expediente": date(2026, 3, 12),
                "prorroga_dias": 1,
            },
        )
        r2 = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": ex2,
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
        assert {rows[0].numero_expediente, rows[1].numero_expediente} == {ex1, ex2}
    finally:
        db.session.rollback()


def test_comprobacion_segundo_expediente_envio_sigue_bloqueado(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_solo_comprobacion()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 20),
            },
        )
        with pytest.raises(RuntimeError, match="Ya existe un expediente de envío"):
            complete_expediente_from_actuacion(
                act.id,
                {
                    "expediente_numero": _unique_num(),
                    "fecha_expediente": date(2026, 3, 21),
                },
            )
    finally:
        db.session.rollback()
