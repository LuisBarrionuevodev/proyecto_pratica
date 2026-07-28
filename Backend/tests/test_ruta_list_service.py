"""Tests del listado de rutas (BORRADOR por defecto; estados múltiples + filtro por día)."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.rutas_trabajo.services.ruta_list_service import list_rutas_borrador, list_rutas_trabajo
from app.models import RutaTrabajo, User


def test_list_rutas_borrador_rejects_invalid_page() -> None:
    """page debe ser >= 1."""
    with pytest.raises(ValueError, match="page"):
        list_rutas_borrador(page=0)


def test_list_rutas_trabajo_rejects_invalid_estado() -> None:
    with pytest.raises(ValueError, match="no válido"):
        list_rutas_trabajo(estados=("PUBLICADA", "NO_EXISTE"))


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "PROPAGATE_EXCEPTIONS": True,
            "JWT_SECRET_KEY": "pytest-jwt-secret-key-32bytes-min",
            "RATELIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        yield app
        db.session.rollback()


def _uniq_user() -> User:
    n = random.randint(100000, 999999)
    u = User(
        username=f"rlist_{n}",
        email=f"rlist_{n}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _uniq_ruta_numero() -> int:
    """Número de ruta único por corrida (SmallInteger; evita uq fecha+turno+numero)."""
    return random.randint(2, 32_000)


def _uniq_list_test_date() -> date:
    """Día aislado para listados (evita ruido de rutas residuales en BD compartida)."""
    return date(2099, 1, 1) + timedelta(days=random.randint(0, 360))


def test_list_publicadas_filtra_por_fecha_exacta(app_ctx) -> None:
    u = _uniq_user()
    d1 = _uniq_list_test_date()
    d2 = d1 + timedelta(days=1)
    r_a = RutaTrabajo(
        fecha=d1,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    r_b = RutaTrabajo(
        fecha=d2,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    db.session.add_all([r_a, r_b])
    db.session.commit()

    rows, total, per, est = list_rutas_trabajo(
        estados=("PUBLICADA",),
        fecha=d1,
        page=1,
        per_page=50,
    )
    assert est == ("PUBLICADA",)
    assert total == 1
    assert len(rows) == 1
    assert rows[0].id == r_a.id


def test_list_publicadas_multiples_estados(app_ctx) -> None:
    u = _uniq_user()
    d = _uniq_list_test_date()
    r_pub = RutaTrabajo(
        fecha=d,
        turno="TARDE",
        estado_ruta="PUBLICADA",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    r_cur = RutaTrabajo(
        fecha=d,
        turno="MANIANA",
        estado_ruta="EN_CURSO",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    r_bor = RutaTrabajo(
        fecha=d,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    db.session.add_all([r_pub, r_cur, r_bor])
    db.session.commit()

    rows, total, _per, est = list_rutas_trabajo(
        estados=("PUBLICADA", "EN_CURSO"),
        fecha=d,
        page=1,
        per_page=50,
    )
    assert set(est) == {"PUBLICADA", "EN_CURSO"}
    ids = {x.id for x in rows}
    assert r_pub.id in ids and r_cur.id in ids and r_bor.id not in ids
    assert len([r for r in rows if r.id in {r_pub.id, r_cur.id}]) == 2
    assert total >= 2


def test_list_borrador_por_fecha_exacta(app_ctx) -> None:
    u = _uniq_user()
    d = _uniq_list_test_date()
    r = RutaTrabajo(
        fecha=d,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    r2 = RutaTrabajo(
        fecha=d + timedelta(days=1),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=_uniq_ruta_numero(),
        observaciones=None,
        created_by_user_id=u.id,
    )
    db.session.add_all([r, r2])
    db.session.commit()

    rows, total, _ = list_rutas_borrador(fecha=d, page=1, per_page=50)
    assert total == 1
    assert rows[0].id == r.id
