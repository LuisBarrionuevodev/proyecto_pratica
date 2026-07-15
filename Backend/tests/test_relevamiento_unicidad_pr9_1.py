"""
PR9.1 — Unicidad mensual de relevamientos por establecimiento.

Mantiene reglas PR7.5/PR7.6 (rubro, nombre fantasía, ángulo) acotadas al mismo mes/año.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.database import db
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.relevamiento_unicidad_service import (
    RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG,
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
    fecha: str = "2026-03-10",
    tipo: str | None = None,
    nombre_fantasia: str | None = None,
    angulo_esquina: str | None = None,
):
    dom = {"calle": calle, "numero": numero}
    if tipo:
        dom["numero_tipo"] = tipo
    out = {
        "fecha": fecha,
        "inspector_nombre": inspector,
        "domicilio": dom,
        "rubro_nombre": rubro,
    }
    if nombre_fantasia is not None:
        out["nombre_fantasia"] = nombre_fantasia
    if angulo_esquina is not None:
        out["angulo_esquina"] = angulo_esquina
    return out


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


# --- NUMERO: unicidad mensual ---


def test_pr91_numero_mismo_establecimiento_mismo_mes_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91NumDup")
    try:
        p1 = _payload(
            calle=calle,
            numero="34",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-03-10",
            nombre_fantasia="Panadería",
        )
        crear_relevamiento_desde_payload(p1)
        with pytest.raises(ValueError, match="establecimiento en el mismo domicilio"):
            crear_relevamiento_desde_payload({**p1, "fecha": "2026-03-20"})
    finally:
        db.session.rollback()


def test_pr91_numero_mismo_establecimiento_otro_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91NumMes")
    try:
        p1 = _payload(
            calle=calle,
            numero="34",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-03-10",
            nombre_fantasia="Panadería",
        )
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload({**p1, "fecha": "2026-05-10"})
    finally:
        db.session.rollback()


def test_pr91_numero_distinto_rubro_mismo_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    rub2 = Rubro.query.filter(Rubro.id != rub.id).first()
    if rub2 is None:
        pytest.skip("Se requiere un segundo rubro")
    calle = _uniq("Pr91NumRub")
    try:
        p1 = _payload(calle=calle, numero="34", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-05-10")
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload({**p1, "rubro_nombre": rub2.nombre})
    finally:
        db.session.rollback()


def test_pr91_numero_distinto_nombre_mismo_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91NumNom")
    try:
        p1 = _payload(
            calle=calle,
            numero="34",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-05-10",
            nombre_fantasia="Local A",
        )
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload({**p1, "nombre_fantasia": "Local B"})
    finally:
        db.session.rollback()


# --- ESQUINA: unicidad mensual ---


def test_pr91_esquina_mismo_angulo_mismo_mes_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91EsqDup")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Norte",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-03-10",
            tipo="ESQUINA",
            angulo_esquina="NE",
            nombre_fantasia="Kiosco",
        )
        crear_relevamiento_desde_payload(p1)
        with pytest.raises(ValueError, match="misma esquina"):
            crear_relevamiento_desde_payload({**p1, "fecha": "2026-03-25"})
    finally:
        db.session.rollback()


def test_pr91_esquina_mismo_angulo_distinto_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91EsqMes")
    try:
        p1 = _payload(
            calle=calle,
            numero="y Sur",
            rubro=rub.nombre,
            inspector=ins.nombre,
            fecha="2026-03-10",
            tipo="ESQUINA",
            angulo_esquina="NE",
            nombre_fantasia="Kiosco",
        )
        crear_relevamiento_desde_payload(p1)
        crear_relevamiento_desde_payload({**p1, "fecha": "2026-05-10"})
    finally:
        db.session.rollback()


# --- Batch grid ---


def test_pr91_batch_mismo_mes_bloquea(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91BatchDup")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    try:
        p = _payload(calle=calle, numero="881", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-03-10")
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-03-27",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "881",
            "rubro": rub.nombre,
        }
        resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
        assert resp.ok is False
        assert RELEVAMIENTO_UNICIDAD_NUMERO_MSG in (resp.errors.get("_row") or "")
    finally:
        db.session.rollback()


def test_pr91_batch_otro_mes_permite(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91BatchOk")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    try:
        p = _payload(calle=calle, numero="882", rubro=rub.nombre, inspector=ins.nombre, fecha="2026-03-10")
        crear_relevamiento_desde_payload(p)
        raw = {
            "fecha": "2026-05-27",
            "inspector": ins.nombre,
            "calle": calle,
            "numero": "882",
            "rubro": rub.nombre,
        }
        resp = svc.validate_row(batch_id, "n1", raw, "relevamientos")
        assert resp.ok is True, resp.errors
    finally:
        db.session.rollback()


def test_pr91_batch_lote_mismo_mes_duplicado_interno(app_ctx, require_pr72_migration) -> None:
    ins, rub = _inspector_y_rubro()
    calle = _uniq("Pr91BatchInt")
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind="relevamientos")
    base = {
        "fecha": "2026-03-15",
        "inspector": ins.nombre,
        "calle": calle,
        "numero": "y Oeste",
        "rubro": rub.nombre,
        "angulo_esquina": "SO",
    }
    assert svc.validate_row(batch_id, "a", base, "relevamientos").ok is True
    resp = svc.validate_row(batch_id, "b", base, "relevamientos")
    assert resp.ok is False
    assert RELEVAMIENTO_UNICIDAD_ESTABLECIMIENTO_MSG in (resp.errors.get("_row") or "")
