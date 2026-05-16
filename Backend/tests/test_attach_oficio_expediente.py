"""
Invariantes de attach_oficio / attach_expediente (Etapa 1: sin reasignación silenciosa de FK).
Requiere BD configurada (misma que create_app); cada test hace rollback al final.
"""

from __future__ import annotations

import random

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.attach.expediente import attach_expediente
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.models import Comprobacion


def _unique_acta_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _flush_comprobacion() -> Comprobacion:
    c = Comprobacion(
        numero_acta=_unique_acta_num(),
        anio=2026,
        mes=3,
        motivo="test attach",
    )
    db.session.add(c)
    db.session.flush()
    return c


def test_attach_oficio_crea_nuevo(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        o = attach_oficio(
            {"numero": "45", "anio": 2026, "causa": "A"},
            comprobacion_id=c.id,
        )
        assert o is not None
        assert o.comprobacion_id == c.id
        assert o.numero_oficio == "45"
        assert o.anio == 2026
    finally:
        db.session.rollback()


def test_attach_oficio_mismo_contexto_actualiza_sin_conflicto(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        o1 = attach_oficio(
            {"numero": "45", "anio": 2026, "causa": "primera"},
            comprobacion_id=c.id,
        )
        db.session.flush()
        o2 = attach_oficio(
            {"numero": "45", "anio": 2026, "causa": "segunda"},
            comprobacion_id=c.id,
        )
        assert o1.id == o2.id
        assert o2.causa == "segunda"
        assert o2.comprobacion_id == c.id
    finally:
        db.session.rollback()


def test_attach_oficio_otra_comprobacion_falla(app_ctx) -> None:
    try:
        c1 = _flush_comprobacion()
        c2 = _flush_comprobacion()
        attach_oficio(
            {"numero": "99", "anio": 2026, "causa": "x"},
            comprobacion_id=c1.id,
        )
        db.session.flush()
        with pytest.raises(ValueError, match="ya existe y está asociado a otra comprobación"):
            attach_oficio(
                {"numero": "99", "anio": 2026, "causa": "y"},
                comprobacion_id=c2.id,
            )
    finally:
        db.session.rollback()


def test_attach_oficio_exige_comprobacion(app_ctx) -> None:
    with pytest.raises(ValueError, match="comprobación"):
        attach_oficio({"numero": "1", "anio": 2026}, comprobacion_id=None)


def test_attach_expediente_comprobacion_crea_nuevo(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        ex = attach_expediente(
            {"numero": "1234", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=None,
        )
        assert ex is not None
        assert ex.comprobacion_id == c.id
        assert ex.oficio_id is None
    finally:
        db.session.rollback()


def test_attach_expediente_comprobacion_mismo_contexto_reusa_fila(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        e1 = attach_expediente(
            {"numero": "5555", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=None,
        )
        db.session.flush()
        e2 = attach_expediente(
            {"numero": "5555", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=None,
        )
        assert e1.id == e2.id
        assert e2.comprobacion_id == c.id
    finally:
        db.session.rollback()


def test_attach_expediente_comprobacion_otra_comprobacion_falla(app_ctx) -> None:
    try:
        c1 = _flush_comprobacion()
        c2 = _flush_comprobacion()
        attach_expediente(
            {"numero": "7777", "anio": 2026},
            comprobacion_id=c1.id,
            oficio_id=None,
        )
        db.session.flush()
        with pytest.raises(ValueError, match="ya existe y está asociado a otra comprobación"):
            attach_expediente(
                {"numero": "7777", "anio": 2026},
                comprobacion_id=c2.id,
                oficio_id=None,
            )
    finally:
        db.session.rollback()


def test_attach_expediente_oficio_crea_y_reusa_mismo_oficio(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        of = attach_oficio(
            {"numero": "10", "anio": 2026},
            comprobacion_id=c.id,
        )
        db.session.flush()
        e1 = attach_expediente(
            {"numero": "8888", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=of.id,
        )
        db.session.flush()
        e2 = attach_expediente(
            {"numero": "8888", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=of.id,
        )
        assert e1.id == e2.id
        assert e2.oficio_id == of.id
    finally:
        db.session.rollback()


def test_attach_expediente_oficio_otro_oficio_falla(app_ctx) -> None:
    try:
        c = _flush_comprobacion()
        o1 = attach_oficio({"numero": "20", "anio": 2026}, comprobacion_id=c.id)
        o2 = attach_oficio({"numero": "21", "anio": 2026}, comprobacion_id=c.id)
        db.session.flush()
        attach_expediente(
            {"numero": "9999", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=o1.id,
        )
        db.session.flush()
        with pytest.raises(ValueError, match="ya existe y está asociado a otro oficio"):
            attach_expediente(
                {"numero": "9999", "anio": 2026},
                comprobacion_id=c.id,
                oficio_id=o2.id,
            )
    finally:
        db.session.rollback()


def test_attach_expediente_soft_deleted_mismo_circuito_reactiva(app_ctx) -> None:
    from datetime import datetime, timezone

    try:
        c = _flush_comprobacion()
        e1 = attach_expediente(
            {"numero": "424242", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=None,
        )
        db.session.flush()
        e1.deleted_at = datetime.now(timezone.utc)
        db.session.add(e1)
        db.session.flush()
        e2 = attach_expediente(
            {"numero": "424242", "anio": 2026},
            comprobacion_id=c.id,
            oficio_id=None,
        )
        assert e2.id == e1.id
        assert e2.deleted_at is None
    finally:
        db.session.rollback()


def test_attach_expediente_exige_comprobacion(app_ctx) -> None:
    with pytest.raises(ValueError, match="comprobación"):
        attach_expediente({"numero": "1", "anio": 2026}, comprobacion_id=None, oficio_id=None)
