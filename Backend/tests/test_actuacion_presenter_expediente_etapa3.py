"""
Etapa 3: salida canónica actas — expediente_* solo envío (oficio_id NULL);
oficio_* desde tabla Oficio (no vía expediente de respuesta).
"""

from __future__ import annotations

import random
from datetime import date

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    expediente_envio_por_comprobacion,
    oficio_por_comprobacion,
)
from app.models import Actuaciones, Comprobacion, Expediente, Oficio, OrdenTrabajo


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _seed_actuacion_con_comprobacion() -> tuple[Actuaciones, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_ot_num(), anio=2026, mes=3, motivo="test")
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


def test_caso1_solo_expediente_comprobacion_en_grid(app_ctx) -> None:
    try:
        act, comp = _seed_actuacion_con_comprobacion()
        db.session.add(
            Expediente(
                numero_expediente="001111",
                anio="2026",
                tipo_expediente="ENVIO_ACTA",
                comprobacion_id=comp.id,
                oficio_id=None,
            )
        )
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["expediente_numero"] == "001111"
        assert row["expediente_anio"] == "2026"
        assert row["oficio_numero"] is None
    finally:
        db.session.rollback()


def test_caso2_solo_oficio_y_expediente_respuesta_no_contamina_expediente_star(app_ctx) -> None:
    try:
        act, comp = _seed_actuacion_con_comprobacion()
        of = Oficio(
            numero_oficio="55",
            anio=2026,
            comprobacion_id=comp.id,
        )
        db.session.add(of)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="009999",
                anio="2026",
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp.id,
                oficio_id=of.id,
            )
        )
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["expediente_numero"] is None
        assert row["expediente_anio"] is None
        assert row["oficio_numero"] == "55"
        assert row["oficio_anio"] == 2026
    finally:
        db.session.rollback()


def test_caso3_ambos_expedientes_expediente_star_es_solo_envio(app_ctx) -> None:
    try:
        act, comp = _seed_actuacion_con_comprobacion()
        db.session.add(
            Expediente(
                numero_expediente="001111",
                anio="2026",
                tipo_expediente="ENVIO_ACTA",
                comprobacion_id=comp.id,
                oficio_id=None,
            )
        )
        db.session.flush()
        of = Oficio(
            numero_oficio="77",
            anio=2026,
            comprobacion_id=comp.id,
        )
        db.session.add(of)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="008888",
                anio="2026",
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp.id,
                oficio_id=of.id,
            )
        )
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["expediente_numero"] == "001111"
        assert row["expediente_anio"] == "2026"
        assert row["oficio_numero"] == "77"
    finally:
        db.session.rollback()


def test_caso4_oficio_explicito_coincide_con_helper(app_ctx) -> None:
    try:
        _, comp = _seed_actuacion_con_comprobacion()
        of = Oficio(numero_oficio="99", anio=2026, comprobacion_id=comp.id, causa="X")
        db.session.add(of)
        db.session.flush()
        got = oficio_por_comprobacion(comp.id)
        assert got is not None
        assert got.numero_oficio == "99"
        assert got.causa == "X"
    finally:
        db.session.rollback()


def test_expediente_envio_helper_excluye_respuesta(app_ctx) -> None:
    try:
        _, comp = _seed_actuacion_con_comprobacion()
        of = Oficio(numero_oficio="1", anio=2026, comprobacion_id=comp.id)
        db.session.add(of)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="002222",
                anio="2026",
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp.id,
                oficio_id=of.id,
            )
        )
        db.session.flush()
        assert expediente_envio_por_comprobacion(comp.id) is None
    finally:
        db.session.rollback()
