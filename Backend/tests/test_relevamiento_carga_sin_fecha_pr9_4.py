"""
PR9.4 — Carga masiva de relevamientos sin columna Fecha.

La fecha efectiva se asigna en el servidor al guardar/validar el lote.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_NUMERO_MSG,
)
from app.models import Inspector, Rubro


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 (revision b7e8f9a0c1d2) aplicada en BD")


def _inspector_y_rubro():
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere al menos un inspector y un rubro en la BD de test")
    return ins, rub


def _payload(
    *,
    calle: str,
    numero: str,
    rubro: str,
    inspector: str,
    fecha: str | None = "2026-03-10",
):
    out = {
        "inspector_nombre": inspector,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rubro,
    }
    if fecha is not None:
        out["fecha"] = fecha
    return out


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _raw_grid(
    *,
    calle: str,
    numero: str,
    rubro: str,
    inspector: str,
    fecha: str | None = None,
) -> dict:
    raw = {
        "inspector": inspector,
        "calle": calle,
        "numero": numero,
        "rubro": rubro,
    }
    if fecha is not None:
        raw["fecha"] = fecha
    return raw


def test_pr94_create_sin_fecha_asigna_fecha_actual(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94Create")
    fixed = date(2026, 7, 16)
    try:
        p = _payload(calle=calle, numero="10", rubro=rub.nombre, inspector=ins.nombre, fecha=None)
        with patch("app.domains.relevamientos.services.create_service.date") as mock_date:
            mock_date.today.return_value = fixed
            rel = crear_relevamiento_desde_payload(p)
        assert rel.fecha == fixed
        assert rel.mes == fixed.month
        assert rel.anio == fixed.year
    finally:
        db.session.rollback()


def test_pr94_batch_sin_fecha_usa_fecha_lote(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94BatchDate")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    st = store.get(batch_id)
    st.fecha_relevamiento_default = date(2026, 3, 18)
    try:
        raw = _raw_grid(calle=calle, numero="22", rubro=rub.nombre, inspector=ins.nombre)
        resp = svc.validate_row(batch_id, "r1", raw, "relevamientos")
        assert resp.ok is True, resp.errors
        assert resp.normalized is not None
        assert resp.normalized["fecha"] == "2026-03-18"
    finally:
        db.session.rollback()


def test_pr94_batch_filas_comparten_fecha_efectiva(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94BatchShared")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    st = store.get(batch_id)
    st.fecha_relevamiento_default = date(2026, 4, 5)
    try:
        base = _raw_grid(calle=calle, numero="33", rubro=rub.nombre, inspector=ins.nombre)
        r1 = svc.validate_row(batch_id, "a", base, "relevamientos")
        r2 = svc.validate_row(
            batch_id,
            "b",
            {**base, "numero": "44", "rubro": rub.nombre},
            "relevamientos",
        )
        assert r1.ok and r2.ok
        assert r1.normalized["fecha"] == "2026-04-05"
        assert r2.normalized["fecha"] == "2026-04-05"
    finally:
        db.session.rollback()


def test_pr94_batch_unicidad_mensual_usa_fecha_efectiva(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94BatchUnic")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    st = store.get(batch_id)
    st.fecha_relevamiento_default = date(2026, 3, 20)
    try:
        crear_relevamiento_desde_payload(
            _payload(calle=calle, numero="55", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-03-10")
        )
        raw = _raw_grid(calle=calle, numero="55", rubro=rub.nombre, inspector=ins.nombre)
        resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
        assert resp.ok is False
        assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (resp.errors.get("_row") or "")
    finally:
        db.session.rollback()


def test_pr94_batch_duplicado_interno_sin_fecha(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94BatchDup")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    st = store.get(batch_id)
    st.fecha_relevamiento_default = date(2026, 3, 21)
    try:
        base = _raw_grid(calle=calle, numero="66", rubro=rub.nombre, inspector=ins.nombre)
        assert svc.validate_row(batch_id, "a", base, "relevamientos").ok is True
        resp = svc.validate_row(batch_id, "b", base, "relevamientos")
        assert resp.ok is False
        assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (resp.errors.get("_row") or "")
    finally:
        db.session.rollback()


def test_pr94_batch_legacy_con_fecha_respeta_fecha_enviada(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr94Legacy")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    st = store.get(batch_id)
    st.fecha_relevamiento_default = date(2026, 3, 1)
    try:
        crear_relevamiento_desde_payload(
            _payload(calle=calle, numero="77", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-03-10")
        )
        raw = _raw_grid(
            calle=calle,
            numero="77",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-05-27",
        )
        resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
        assert resp.ok is True, resp.errors
        assert resp.normalized["fecha"] == "2026-05-27"
    finally:
        db.session.rollback()
