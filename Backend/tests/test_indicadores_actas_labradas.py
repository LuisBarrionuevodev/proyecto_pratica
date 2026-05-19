"""
Reglas de actas labradas en indicadores (excluye previas/origen).
Requiere BD; rollback al final de cada test.
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from app.models import Actuaciones, Comprobacion, Inspeccion, Motivo, Notificacion, OrdenTrabajo


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion(fecha: date | None = None) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha or date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_actas_labradas_excluye_notificacion_previa_sin_motivos(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        n = Notificacion(numero_acta=_unique_ot_num(), anio=2026, mes=3)
        db.session.add(n)
        db.session.flush()
        act.notificacion_id = n.id
        db.session.flush()

        res = build_indicadores_resumen(date(2026, 3, 1), date(2026, 3, 31))
        assert res.actas_por_tipo.notificacion == 0
    finally:
        db.session.rollback()


def test_actas_labradas_cuenta_notificacion_con_motivos(app_ctx) -> None:
    try:
        m = Motivo.query.first()
        if m is None:
            m = Motivo(nombre=f"mt_{_unique_ot_num()}")
            db.session.add(m)
            db.session.flush()

        act = _mk_actuacion()
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()

        res = build_indicadores_resumen(date(2026, 3, 1), date(2026, 3, 31))
        assert res.actas_por_tipo.notificacion >= 1
    finally:
        db.session.rollback()


def test_actas_labradas_excluye_comprobacion_previa_pendiente(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        resolver_previas(
            act,
            {
                "comprobacion_previa_num": _unique_ot_num(),
                "comprobacion_previa_motivo": None,
            },
        )
        db.session.flush()
        assert act.comprobacion_id is not None
        comp = db.session.get(Comprobacion, act.comprobacion_id)
        assert comp is not None
        assert comp.motivo == "PENDIENTE"

        res = build_indicadores_resumen(date(2026, 3, 1), date(2026, 3, 31))
        assert res.actas_por_tipo.comprobacion == 0
    finally:
        db.session.rollback()


def test_actas_labradas_cuenta_comprobacion_labrada(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        attach_comprobacion(
            act,
            {"acta_num": _unique_ot_num(), "motivo": "Incumplimiento normativa"},
        )
        db.session.flush()

        res = build_indicadores_resumen(date(2026, 3, 1), date(2026, 3, 31))
        assert res.actas_por_tipo.comprobacion >= 1
    finally:
        db.session.rollback()


def test_actas_labradas_cuenta_inspeccion(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        db.session.add(
            Inspeccion(
                actuacion_id=act.id,
                numero_acta=_unique_ot_num(),
                anio=2026,
                mes=3,
            )
        )
        db.session.flush()

        res = build_indicadores_resumen(date(2026, 3, 1), date(2026, 3, 31))
        assert res.actas_por_tipo.inspeccion >= 1
        assert any(m.inspeccion >= 1 for m in res.actas_labradas_mensual)
    finally:
        db.session.rollback()
