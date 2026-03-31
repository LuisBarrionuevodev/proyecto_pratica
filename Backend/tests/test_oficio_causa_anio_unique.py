"""
Unicidad (causa, anio) en Oficio: misma causa puede repetirse en otros años.
Requiere BD con constraint uq_of_causa_anio (migración aplicada).
"""

from __future__ import annotations

import random

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.models import Comprobacion


def _uniq_num() -> str:
    return str(random.randint(100000, 999999))


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_comprobacion() -> Comprobacion:
    c = Comprobacion(
        numero_acta=_uniq_num(),
        anio=2026,
        mes=3,
        motivo="test causa anio",
    )
    db.session.add(c)
    db.session.flush()
    return c


def test_crea_oficio_causa_nueva_ok(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        n = _uniq_num()
        o = attach_oficio(
            {"numero": n, "anio": 2026, "causa": "501"},
            comprobacion_id=c.id,
        )
        assert o is not None
        assert o.causa == "501"
    finally:
        db.session.rollback()


def test_misma_causa_mismo_anio_otro_numero_falla(app_ctx) -> None:
    try:
        c1 = _mk_comprobacion()
        c2 = _mk_comprobacion()
        n1, n2 = _uniq_num(), _uniq_num()
        attach_oficio(
            {"numero": n1, "anio": 2026, "causa": "777"},
            comprobacion_id=c1.id,
        )
        db.session.flush()
        with pytest.raises(ValueError, match='La causa "777" ya existe para el año 2026'):
            attach_oficio(
                {"numero": n2, "anio": 2026, "causa": "777"},
                comprobacion_id=c2.id,
            )
    finally:
        db.session.rollback()


def test_misma_causa_distinto_anio_ok(app_ctx) -> None:
    try:
        c1 = _mk_comprobacion()
        c2 = _mk_comprobacion()
        n1, n2 = _uniq_num(), _uniq_num()
        attach_oficio(
            {"numero": n1, "anio": 2026, "causa": "888"},
            comprobacion_id=c1.id,
        )
        db.session.flush()
        o2 = attach_oficio(
            {"numero": n2, "anio": 2027, "causa": "888"},
            comprobacion_id=c2.id,
        )
        db.session.flush()
        assert o2.anio == 2027
        assert o2.causa == "888"
    finally:
        db.session.rollback()


def test_actualizar_mismo_oficio_misma_causa_ok(app_ctx) -> None:
    try:
        c = _mk_comprobacion()
        n = _uniq_num()
        o1 = attach_oficio(
            {"numero": n, "anio": 2026, "causa": "100"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        o2 = attach_oficio(
            {"numero": n, "anio": 2026, "causa": "100"},
            comprobacion_id=c.id,
        )
        assert o1.id == o2.id
        assert o2.causa == "100"
    finally:
        db.session.rollback()


def test_multiples_oficios_causa_null_mismo_anio_ok(app_ctx) -> None:
    """PostgreSQL: varias filas con causa NULL y mismo año no violan uq_of_causa_anio."""
    try:
        c1 = _mk_comprobacion()
        c2 = _mk_comprobacion()
        n1, n2 = _uniq_num(), _uniq_num()
        o1 = attach_oficio(
            {"numero": n1, "anio": 2026, "causa": None},
            comprobacion_id=c1.id,
        )
        o2 = attach_oficio(
            {"numero": n2, "anio": 2026, "causa": None},
            comprobacion_id=c2.id,
        )
        db.session.flush()
        assert o1.id != o2.id
        assert o1.causa is None
        assert o2.causa is None
    finally:
        db.session.rollback()
