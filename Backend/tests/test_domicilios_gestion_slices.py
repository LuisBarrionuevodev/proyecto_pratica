"""Filtro ``slice`` en GET /map/pendientes (Gestión Domicilios PR2)."""

from __future__ import annotations

import random

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.map_service import list_pendientes
from app.models import Domicilio, DomicilioGeocode


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_dom(*, calle_status: str, geo_status: str | None = None, source: str = "AUTO") -> Domicilio:
    dom = Domicilio(
        calle=f"CalleSlice{_unique_num()}",
        numero="50",
        calle_norm_status=calle_status,
        calle_norm_score=1.0 if calle_status == "OK" else None,
    )
    db.session.add(dom)
    db.session.flush()
    if geo_status is not None:
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status=geo_status,
            source=source,
            lat=-26.824 if geo_status == "OK" else None,
            lng=-65.222 if geo_status == "OK" else None,
            score=0.98 if geo_status == "OK" else None,
        )
        db.session.add(geo)
        db.session.flush()
    return dom


def test_sin_slice_conserva_campos_legacy(app_ctx) -> None:
    try:
        _mk_dom(calle_status="PENDIENTE")
        items = list_pendientes(slice=None)
        assert items
        assert "slice" not in items[0]
        assert "score_unificado" not in items[0]
    finally:
        db.session.rollback()


def test_slice_nomenclatura_pendiente(app_ctx) -> None:
    try:
        pend = _mk_dom(calle_status="PENDIENTE")
        ok = _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(slice="nomenclatura_pendiente")
        ids = {i["domicilio_id"] for i in items}
        assert pend.id in ids
        assert ok.id not in ids
        assert all(i.get("slice") == "nomenclatura_pendiente" for i in items)
    finally:
        db.session.rollback()


def test_slice_geo_pendiente(app_ctx) -> None:
    try:
        geo_pend = _mk_dom(calle_status="OK", geo_status=None)
        ok = _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(slice="geo_pendiente")
        ids = {i["domicilio_id"] for i in items}
        assert geo_pend.id in ids
        assert ok.id not in ids
    finally:
        db.session.rollback()


def test_slice_ok(app_ctx) -> None:
    try:
        ok = _mk_dom(calle_status="OK", geo_status="OK")
        pend = _mk_dom(calle_status="PENDIENTE")
        items = list_pendientes(slice="ok")
        ids = {i["domicilio_id"] for i in items}
        assert ok.id in ids
        assert pend.id not in ids
    finally:
        db.session.rollback()


def test_slice_all_incluye_varios_estados(app_ctx) -> None:
    try:
        pend = _mk_dom(calle_status="PENDIENTE")
        ok = _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(slice="all")
        ids = {i["domicilio_id"] for i in items}
        assert pend.id in ids
        assert ok.id in ids
        assert all("slice" in i for i in items)
    finally:
        db.session.rollback()


def test_kind_norm_sin_slice_no_roto(app_ctx) -> None:
    try:
        pend = _mk_dom(calle_status="PENDIENTE")
        _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(kind="norm", slice=None)
        ids = {i["domicilio_id"] for i in items}
        assert pend.id in ids
        assert "slice" not in items[0]
        assert "match_strategy" not in items[0]
    finally:
        db.session.rollback()


def test_slice_incluye_match_strategy_opcional(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """PR6A.1: con slice= se exponen match_strategy y confidence_reason si existen."""

    def _fake_fields(dom: Domicilio) -> dict:
        return {
            "match_strategy": "exact_tokens",
            "confidence_reason": "Coincidencia exacta por tokens",
        }

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.map_service.nomenclatura_match_fields",
        _fake_fields,
    )
    try:
        dom = _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(slice="ok")
        row = next(i for i in items if i["domicilio_id"] == dom.id)
        assert row.get("match_strategy") == "exact_tokens"
        assert row.get("confidence_reason") == "Coincidencia exacta por tokens"
    finally:
        db.session.rollback()


def test_slice_sin_strategy_no_rompe(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """PR6A.1: filas sin estrategia no incluyen claves o vienen vacías."""

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.map_service.nomenclatura_match_fields",
        lambda _dom: {},
    )
    try:
        dom = _mk_dom(calle_status="OK", geo_status="OK")
        items = list_pendientes(slice="ok")
        row = next(i for i in items if i["domicilio_id"] == dom.id)
        assert row.get("match_strategy") is None
        assert row.get("confidence_reason") is None
    finally:
        db.session.rollback()
