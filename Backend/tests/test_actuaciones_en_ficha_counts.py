"""Conteos batch por establecimiento_operativo_id (presenter sin N+1)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
    count_actuaciones_por_establecimiento_operativo_ids,
)
from app.models import Actuaciones, OrdenTrabajo


def _unique_ot() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def test_count_empty_ids(app_ctx) -> None:
    assert count_actuaciones_por_establecimiento_operativo_ids([]) == {}


def test_count_groups_by_ficha(app_ctx) -> None:
    """Dos actuaciones con el mismo EO id cuentan 2; otra ficha cuenta aparte."""
    from app.models import EstablecimientoOperativo, Domicilio, User

    u = User(
        username=f"u_cnt_{random.randint(0, 999999)}",
        email=f"cnt_{random.randint(0, 999999)}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()

    d1 = Domicilio(calle=f"CalleCnt{random.randint(0, 99999)}", numero="1")
    d2 = Domicilio(calle=f"CalleCnt{random.randint(0, 99999)}", numero="2")
    db.session.add_all([d1, d2])
    db.session.flush()

    eo1 = EstablecimientoOperativo(domicilio_id=d1.id, created_by_user_id=u.id)
    eo2 = EstablecimientoOperativo(domicilio_id=d2.id, created_by_user_id=u.id)
    db.session.add_all([eo1, eo2])
    db.session.flush()

    def _mk_act(eo_id: int) -> Actuaciones:
        ot = OrdenTrabajo(numero_acta=_unique_ot(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()
        a = Actuaciones(
            fecha=date(2026, 3, 1),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            establecimiento_operativo_id=eo_id,
        )
        db.session.add(a)
        db.session.flush()
        return a

    _mk_act(eo1.id)
    _mk_act(eo1.id)
    _mk_act(eo2.id)
    db.session.commit()

    m = count_actuaciones_por_establecimiento_operativo_ids([eo1.id, eo2.id, 999_999_999])
    assert m[eo1.id] == 2
    assert m[eo2.id] == 1
    assert 999_999_999 not in m

    acts = Actuaciones.query.filter(Actuaciones.establecimiento_operativo_id == eo1.id).all()
    assert build_counts_by_eo_from_actuaciones(acts) == {eo1.id: 2}

    db.session.rollback()
