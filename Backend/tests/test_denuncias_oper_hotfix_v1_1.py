"""
HOTFIX V1.1-OPER.1 — Denuncias: geocode post-commit, sin bloqueo HTTP.
"""

from __future__ import annotations

import time
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.models import Denuncia, GeocodePostCommitJob, IniciadorRuta, User


def _unique_num() -> str:
    return f"{int(time.time() * 1000) % 1000000:06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _ensure_active_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"oper11_{_unique_num()}",
        email=f"oper11_{_unique_num()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture
def mock_user(monkeypatch):
    u = _ensure_active_user()
    monkeypatch.setattr(
        "app.domains.denuncias.services.denuncias_service.get_current_user_id",
        lambda: int(u.id),
    )
    return u


@patch("app.domains.denuncias.services.denuncias_service.schedule_geocode_after_grid_commit")
@patch("app.domains.denuncias.services.denuncias_service.on_domicilio_changed")
def test_crear_denuncia_persiste_y_encola_geocode_sin_sync(
    mock_on_changed, mock_schedule, app_ctx, mock_user
) -> None:
    mock_schedule.return_value = [1]
    calle = _uniq("Oper11")
    try:
        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 10, 2),
            domicilio_id=None,
            calle=calle,
            numero="123",
            interseccion=None,
            motivo="Ruidos",
        )
        assert den.id is not None
        assert ini.denuncia_id == den.id
        assert ini.tipo_iniciador == "DENUNCIA"
        mock_on_changed.assert_not_called()
        mock_schedule.assert_called_once()
        assert mock_schedule.call_args[0][0] == [den.domicilio_id]
    finally:
        db.session.rollback()


@patch("app.domains.denuncias.services.denuncias_service.on_domicilio_changed")
def test_crear_denuncia_encola_en_tabla_post_commit(mock_on_changed, app_ctx, mock_user) -> None:
    from sqlalchemy import inspect

    if not inspect(db.engine).has_table("geocode_post_commit_job"):
        GeocodePostCommitJob.__table__.create(bind=db.engine, checkfirst=True)
    GeocodePostCommitJob.query.delete()
    db.session.commit()

    mock_on_changed.side_effect = AssertionError("geocode sync no debe ejecutarse en POST")

    calle = _uniq("Oper11Q")
    try:
        den, _ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 10, 2),
            domicilio_id=None,
            calle=calle,
            numero="45",
            interseccion=None,
            motivo="Higiene",
        )
        mock_on_changed.assert_not_called()
        jobs = GeocodePostCommitJob.query.filter(
            GeocodePostCommitJob.domicilio_id == den.domicilio_id
        ).all()
        assert len(jobs) >= 1
    finally:
        db.session.rollback()


@patch("app.domains.denuncias.services.denuncias_service.schedule_geocode_after_grid_commit")
def test_crear_denuncia_si_falla_encolado_sigue_creada(mock_schedule, app_ctx, mock_user) -> None:
    mock_schedule.side_effect = RuntimeError("enqueue failed")
    calle = _uniq("Oper11Fail")
    try:
        den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 10, 2),
            domicilio_id=None,
            calle=calle,
            numero="9",
            interseccion=None,
            motivo="Olor",
        )
        assert db.session.get(Denuncia, den.id) is not None
        assert db.session.get(IniciadorRuta, ini.id) is not None
    finally:
        db.session.rollback()


@patch("app.domains.denuncias.services.denuncias_service.schedule_geocode_after_grid_commit")
@patch("app.domains.denuncias.services.denuncias_service.on_domicilio_changed")
def test_creaciones_consecutivas_no_esperan_geocode_sync(
    mock_on_changed, mock_schedule, app_ctx, mock_user
) -> None:
    def slow_geocode(_domicilio_id: int) -> None:
        time.sleep(2)

    mock_on_changed.side_effect = slow_geocode
    mock_schedule.return_value = []

    t0 = time.monotonic()
    try:
        for i in range(3):
            crear_denuncia_con_iniciador(
                fecha=date(2026, 10, 2),
                domicilio_id=None,
                calle=_uniq(f"Oper11Seq{i}"),
                numero=str(100 + i),
                interseccion=None,
                motivo=f"Motivo {i}",
            )
        elapsed = time.monotonic() - t0
        assert elapsed < 1.5
        mock_on_changed.assert_not_called()
        assert mock_schedule.call_count == 3
    finally:
        db.session.rollback()


def test_create_denuncia_route_500_sin_detalle_interno(client, auth_headers, monkeypatch) -> None:
    def boom(**_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(
        "app.domains.denuncias.routes.crear_denuncia_con_iniciador",
        boom,
    )
    resp = client.post(
        "/api/denuncias",
        json={
            "fecha": "2026-10-02",
            "calle": "Test",
            "numero": "1",
            "motivo": "x",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert body.get("detail") == "Error interno del servidor."
    assert "secret" not in str(body)
