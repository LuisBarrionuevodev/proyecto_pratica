"""Servicio resolve_establecimiento_por_domicilio (ficha 1:1 con domicilio)."""

from __future__ import annotations

import random

import pytest

from app.database import db
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.models import Domicilio, EstablecimientoOperativo, User


def _unique_calle() -> str:
    return f"TestCalle{random.randint(0, 999999)}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    n = random.randint(0, 999999)
    u = User(
        username=f"u_est_op_{n}",
        email=f"est_op_{n}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_domicilio() -> Domicilio:
    d = Domicilio(calle=_unique_calle(), numero="123")
    db.session.add(d)
    db.session.flush()
    return d


def test_resolve_none_domicilio_returns_none(app_ctx) -> None:
    assert resolve_establecimiento_por_domicilio(None, created_by_user_id=1) is None


def test_resolve_missing_domicilio_returns_none(app_ctx) -> None:
    assert resolve_establecimiento_por_domicilio(999_999_999, created_by_user_id=1) is None


def test_resolve_creates_then_reuses_same_row(app_ctx) -> None:
    user = _mk_user()
    dom = _mk_domicilio()

    first = resolve_establecimiento_por_domicilio(dom.id, created_by_user_id=user.id)
    assert first is not None
    second = resolve_establecimiento_por_domicilio(dom.id, created_by_user_id=user.id)
    assert second == first

    db.session.commit()

    rows = EstablecimientoOperativo.query.filter_by(domicilio_id=dom.id).all()
    assert len(rows) == 1
    assert rows[0].id == first
    assert rows[0].created_by_user_id == user.id

    db.session.rollback()


def test_resolve_skips_soft_deleted_domicilio(app_ctx) -> None:
    from datetime import UTC, datetime

    user = _mk_user()
    dom = _mk_domicilio()

    dom.deleted_at = datetime.now(UTC)
    db.session.add(dom)
    db.session.flush()

    assert resolve_establecimiento_por_domicilio(dom.id, created_by_user_id=user.id) is None
    db.session.rollback()
