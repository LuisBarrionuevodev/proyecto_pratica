"""Tests PR6C.1 perf + PR6C.2/3 contrato GET /map/gestion-domicilios."""

from __future__ import annotations

import logging
import random

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_query import (
    GestionDomiciliosQuery,
)
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_response import (
    GestionDomiciliosResponse,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_service import (
    get_last_gestion_domicilios_perf,
    list_gestion_domicilios,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_status import (
    resolve_geo_chip,
    resolve_status_operativo,
)
from app.domains.geolocalizacion.geocode.services.map_service import (
    get_last_pendientes_perf,
    list_pendientes,
)
from app.models import Domicilio, DomicilioGeocode
from app.shared import perf_log

TEST_CALLE_PREFIX = "GDomTest"


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_dom(*, calle_status: str, geo_status: str | None = None) -> Domicilio:
    dom = Domicilio(
        calle=f"PerfBench{_unique_num()}",
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
            source="AUTO",
            lat=-26.824 if geo_status == "OK" else None,
            lng=-65.222 if geo_status == "OK" else None,
            score=0.98 if geo_status == "OK" else None,
        )
        db.session.add(geo)
        db.session.flush()
    return dom


def _mk_gestion_dom(
    *,
    tag: str | None = None,
    numero: str = "100",
    calle_norm_status: str = "OK",
    geo_status: str | None = "OK",
    source: str = "AUTO",
    lat: float | None = -26.824,
    lng: float | None = -65.222,
    score: float | None = 0.98,
    quality: str | None = "building",
    with_geo: bool = True,
) -> Domicilio:
    suffix = tag or _unique_num()
    dom = Domicilio(
        calle=f"{TEST_CALLE_PREFIX}{suffix}",
        numero=numero,
        calle_normalizada=f"Calle {suffix}",
        calle_norm_status=calle_norm_status,
        calle_norm_score=1.0 if calle_norm_status == "OK" else None,
    )
    db.session.add(dom)
    db.session.flush()
    if with_geo and geo_status is not None:
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            geo_status=geo_status,
            source=source,
            lat=lat,
            lng=lng,
            score=score,
            quality=quality,
        )
        db.session.add(geo)
        db.session.flush()
    return dom


def _row_by_id(rows: list, domicilio_id: int):
    return next(r for r in rows if r.domicilio_id == domicilio_id)


def test_gestion_domicilios_returns_valid_shape(app_ctx) -> None:
    try:
        body = list_gestion_domicilios(GestionDomiciliosQuery(page=3, page_size=10))
        parsed = GestionDomiciliosResponse.model_validate(body.model_dump())
        assert parsed.pagination.page == 3
        assert parsed.pagination.page_size == 10
        assert parsed.summary.total >= 0
    finally:
        db.session.rollback()


def test_geo_chip_sin_coords(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="SinCoords", with_geo=False)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=dom.calle, status_operativo="sin_punto", page_size=100)
        )
        row = _row_by_id(body.rows, dom.id)
        assert row.geo_chip == "SIN_COORDS"
        assert row.has_coordinates is False
        assert row.lat is None
        assert row.lng is None
    finally:
        db.session.rollback()


def test_geo_chip_en_mapa(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="EnMapa", geo_status="OK", lat=-26.82, lng=-65.22)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=dom.calle, status_operativo="geolocalizado", page_size=100)
        )
        row = _row_by_id(body.rows, dom.id)
        assert row.geo_chip == "EN_MAPA"
        assert row.has_coordinates is True
        assert row.lat is not None
        assert row.lng is not None
    finally:
        db.session.rollback()


def test_filtro_sin_punto(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="FiltroSP", with_geo=False)
        ok = _mk_gestion_dom(tag="FiltroOK", geo_status="OK")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, status_operativo="sin_punto", page_size=100)
        )
        ids = {r.domicilio_id for r in body.rows}
        assert dom.id in ids
        assert ok.id not in ids
    finally:
        db.session.rollback()


def test_filtro_punto_dudoso(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="FiltroPD", geo_status="REVIEW", score=0.5)
        ok = _mk_gestion_dom(tag="FiltroPDOk", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, status_operativo="punto_dudoso", page_size=100)
        )
        ids = {r.domicilio_id for r in body.rows}
        assert dom.id in ids
        assert ok.id not in ids
    finally:
        db.session.rollback()


def test_filtro_manual(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="FiltroMan", source="MANUAL", geo_status="OK")
        auto = _mk_gestion_dom(tag="FiltroAuto", source="AUTO", geo_status="OK")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, status_operativo="manual", page_size=100)
        )
        ids = {r.domicilio_id for r in body.rows}
        assert dom.id in ids
        assert auto.id not in ids
    finally:
        db.session.rollback()


def test_filtro_geolocalizado(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="FiltroGeo", geo_status="OK", source="AUTO", score=0.99)
        manual = _mk_gestion_dom(tag="FiltroGeoMan", source="MANUAL", geo_status="OK")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX, status_operativo="geolocalizado", page_size=100
            )
        )
        ids = {r.domicilio_id for r in body.rows}
        assert dom.id in ids
        assert manual.id not in ids
    finally:
        db.session.rollback()


def test_filtro_requiere_accion(app_ctx) -> None:
    try:
        sin_p = _mk_gestion_dom(tag="ReqSP", with_geo=False)
        dudoso = _mk_gestion_dom(tag="ReqPD", geo_status="REVIEW", score=0.5)
        err = _mk_gestion_dom(tag="ReqErr", geo_status="ERROR", lat=None, lng=None)
        ok = _mk_gestion_dom(tag="ReqOk", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX, status_operativo="requiere_accion", page_size=100
            )
        )
        ids = {r.domicilio_id for r in body.rows}
        assert sin_p.id in ids
        assert dudoso.id in ids
        assert err.id in ids
        assert ok.id not in ids
        for row in body.rows:
            if row.domicilio_id in {sin_p.id, dudoso.id, err.id}:
                assert row.requiere_accion is True
    finally:
        db.session.rollback()


def test_paginacion(app_ctx) -> None:
    try:
        for i in range(3):
            _mk_gestion_dom(tag=f"Pag{i}", numero=str(200 + i))
        body_p1 = list_gestion_domicilios(
            GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, status_operativo="todos", page=1, page_size=2)
        )
        body_p2 = list_gestion_domicilios(
            GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, status_operativo="todos", page=2, page_size=2)
        )
        assert body_p1.pagination.page == 1
        assert body_p1.pagination.page_size == 2
        assert body_p1.pagination.total >= 3
        assert len(body_p1.rows) == 2
        ids_p1 = {r.domicilio_id for r in body_p1.rows}
        ids_p2 = {r.domicilio_id for r in body_p2.rows}
        assert ids_p1.isdisjoint(ids_p2)
    finally:
        db.session.rollback()


def test_q_filtra(app_ctx) -> None:
    try:
        target = _mk_gestion_dom(tag="BuscarQUnique123")
        _mk_gestion_dom(tag="OtroQ999")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q="BuscarQUnique123", status_operativo="todos", page_size=50)
        )
        ids = {r.domicilio_id for r in body.rows}
        assert target.id in ids
        assert all("BuscarQUnique123" in r.domicilio_linea for r in body.rows)
    finally:
        db.session.rollback()


def test_include_map_points_false(app_ctx) -> None:
    try:
        _mk_gestion_dom(tag="NoMapPts", geo_status="OK")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="geolocalizado",
                include_map_points=False,
                page_size=50,
            )
        )
        assert body.map_points == []
        assert body.map_points_meta is None
    finally:
        db.session.rollback()


def test_include_map_points_true_limitado(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="MapPt", geo_status="REVIEW", score=0.5)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=dom.calle,
                status_operativo="punto_dudoso",
                include_map_points=True,
                page_size=10,
            )
        )
        assert len(body.map_points) >= 1
        pt = next(p for p in body.map_points if p.domicilio_id == dom.id)
        assert pt.lat == pytest.approx(-26.824)
        assert pt.lng == pytest.approx(-65.222)
        assert pt.geo_chip == "EN_MAPA"
        assert pt.requiere_accion is True
        assert pt.status_operativo_label == "Punto dudoso"
        assert body.map_points_meta is not None
        assert body.map_points_meta.map_mode == "problematic"
    finally:
        db.session.rollback()


def test_map_mode_manual(app_ctx) -> None:
    try:
        manual = _mk_gestion_dom(tag="MapMan", source="MANUAL", geo_status="OK")
        auto = _mk_gestion_dom(tag="MapAuto", source="AUTO", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="todos",
                map_mode="manual",
                include_map_points=True,
                page_size=10,
            )
        )
        ids = {p.domicilio_id for p in body.map_points}
        assert manual.id in ids
        assert auto.id not in ids
        assert body.map_points_meta is not None
        assert body.map_points_meta.map_mode == "manual"
    finally:
        db.session.rollback()


def test_map_mode_errors(app_ctx) -> None:
    try:
        err = _mk_gestion_dom(
            tag="MapErr",
            geo_status="ERROR",
            lat=-26.83,
            lng=-65.23,
            score=None,
        )
        ok = _mk_gestion_dom(tag="MapErrOk", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="todos",
                map_mode="errors",
                include_map_points=True,
                page_size=10,
            )
        )
        ids = {p.domicilio_id for p in body.map_points}
        assert err.id in ids
        assert ok.id not in ids
    finally:
        db.session.rollback()


def test_map_mode_visible_excluye_solo_error(app_ctx) -> None:
    try:
        err = _mk_gestion_dom(
            tag="VisErr",
            geo_status="ERROR",
            lat=-26.83,
            lng=-65.23,
        )
        geo = _mk_gestion_dom(tag="VisGeo", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="todos",
                map_mode="visible",
                include_map_points=True,
                page_size=10,
            )
        )
        ids = {p.domicilio_id for p in body.map_points}
        assert geo.id in ids
        assert err.id not in ids
    finally:
        db.session.rollback()


def test_bbox_filtra_map_points(app_ctx) -> None:
    try:
        inside = _mk_gestion_dom(tag="BboxIn", lat=-26.824, lng=-65.222)
        outside = _mk_gestion_dom(tag="BboxOut", lat=-27.5, lng=-65.9)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="todos",
                map_mode="all",
                include_map_points=True,
                bbox="-26.9,-65.3,-26.8,-65.2",
                page_size=10,
            )
        )
        ids = {p.domicilio_id for p in body.map_points}
        assert inside.id in ids
        assert outside.id not in ids
        assert body.map_points_meta is not None
        assert body.map_points_meta.bbox_applied is True
    finally:
        db.session.rollback()


def test_bbox_invalido_raises(app_ctx) -> None:
    with pytest.raises(ValueError, match="bbox"):
        list_gestion_domicilios(
            GestionDomiciliosQuery(
                status_operativo="todos",
                bbox="invalid",
                include_map_points=True,
            )
        )


def test_map_points_meta_truncated(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.gestion_domicilios_map_points.MAP_POINTS_LIMIT",
        2,
    )
    try:
        for i in range(3):
            _mk_gestion_dom(tag=f"Trunc{i}", geo_status="OK", score=0.99)
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=TEST_CALLE_PREFIX,
                status_operativo="todos",
                map_mode="all",
                include_map_points=True,
                page_size=10,
            )
        )
        assert body.map_points_meta is not None
        assert body.map_points_meta.returned == 2
        assert body.map_points_meta.truncated is True
        assert body.map_points_meta.total_matching >= 3
    finally:
        db.session.rollback()


def test_no_llama_match_calle(app_ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def _boom(*_args, **_kwargs):
        calls.append(1)
        raise AssertionError("match_calle no debe invocarse en listado común")

    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service.match_calle",
        _boom,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.normalizacion_calles.services.nomenclatura_match_display_service.match_calle",
        _boom,
    )
    try:
        dom = _mk_gestion_dom(tag="NoMatch")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(q=dom.calle, status_operativo="todos", page_size=10)
        )
        assert body.rows
        assert calls == []
    finally:
        db.session.rollback()


def test_include_tecnico_sin_match_strategy(app_ctx) -> None:
    try:
        dom = _mk_gestion_dom(tag="Tecnico")
        body = list_gestion_domicilios(
            GestionDomiciliosQuery(
                q=dom.calle,
                status_operativo="geolocalizado",
                include_tecnico=True,
                page_size=10,
            )
        )
        row = _row_by_id(body.rows, dom.id)
        assert row.tecnico is not None
        assert row.tecnico.nomenclatura_estado is not None
        assert row.tecnico.match_strategy is None
    finally:
        db.session.rollback()


def test_status_resolver_unit() -> None:
    geo_ok = DomicilioGeocode(
        domicilio_id=1,
        geo_status="OK",
        source="AUTO",
        lat=-26.8,
        lng=-65.2,
        score=0.99,
        quality="building",
    )
    assert resolve_status_operativo(None, geo_ok) == "geolocalizado"
    chip, has = resolve_geo_chip(geo_ok)
    assert chip == "EN_MAPA"
    assert has is True


def test_gestion_domicilios_perf_stats(app_ctx) -> None:
    try:
        _mk_gestion_dom(tag="Perf")
        list_gestion_domicilios(GestionDomiciliosQuery(q=TEST_CALLE_PREFIX, page_size=10))
        perf = get_last_gestion_domicilios_perf()
        assert perf.total_ms >= 0
        assert perf.status_operativo == "requiere_accion"
    finally:
        db.session.rollback()


def test_pendientes_perf_stats_populated(app_ctx) -> None:
    try:
        _mk_dom(calle_status="PENDIENTE")
        list_pendientes(slice="nomenclatura_pendiente")
        perf = get_last_pendientes_perf()
        assert perf.rows_sql >= 1
        assert perf.classified_count >= 1
        assert perf.total_ms >= 0
    finally:
        db.session.rollback()


def test_perf_log_no_emite_sin_flag(app_ctx, caplog: pytest.LogCaptureFixture, monkeypatch) -> None:
    monkeypatch.delenv("PERF_LOG", raising=False)
    monkeypatch.setattr(perf_log, "perf_log_enabled", lambda: False)
    caplog.set_level(logging.INFO)
    try:
        _mk_dom(calle_status="OK", geo_status="OK")
        list_pendientes(slice="ok")
        perf_logs = [r for r in caplog.records if r.message.startswith("perf.")]
        assert perf_logs == []
    finally:
        db.session.rollback()


def test_benchmark_script_imports() -> None:
    from app.scripts import benchmark_gestion_domicilios as mod

    assert mod.BENCHMARK_CASES
    assert callable(mod.run_benchmark)


def test_gestion_domicilios_query_defaults() -> None:
    q = GestionDomiciliosQuery()
    assert q.status_operativo == "requiere_accion"
    assert q.page == 1
    assert q.page_size == 50
    assert q.include_map_points is True
    assert q.include_tecnico is False


def test_gestion_domicilios_query_from_request_args() -> None:
    q = GestionDomiciliosQuery.from_request_args(
        {
            "q": "san martin",
            "page": "2",
            "page_size": "25",
            "status_operativo": "sin_punto",
            "include_map_points": "0",
            "include_tecnico": "1",
        }
    )
    assert q.q == "san martin"
    assert q.page == 2
    assert q.page_size == 25
    assert q.status_operativo == "sin_punto"
    assert q.include_map_points is False
    assert q.include_tecnico is True


def test_gestion_domicilios_endpoint_http_shape(client, auth_headers) -> None:
    resp = client.get("/api/map/gestion-domicilios?page=1&page_size=50", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) == {"summary", "rows", "map_points", "map_points_meta", "pagination"}
    assert set(data["summary"].keys()) == {
        "total",
        "requieren_accion",
        "sin_punto",
        "punto_dudoso",
        "errores",
        "manuales",
        "geolocalizados",
    }
    assert isinstance(data["rows"], list)
    assert isinstance(data["map_points"], list)
    assert data["map_points_meta"] is None or isinstance(data["map_points_meta"], dict)
    assert data["pagination"]["page"] == 1


def test_gestion_domicilios_invalid_page_returns_422(client, auth_headers) -> None:
    resp = client.get("/api/map/gestion-domicilios?page=0", headers=auth_headers)
    assert resp.status_code == 422


def test_gestion_domicilios_invalid_bbox_returns_422(client, auth_headers) -> None:
    resp = client.get(
        "/api/map/gestion-domicilios?bbox=invalid&include_map_points=1",
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_pendientes_sin_slice_sigue_igual(app_ctx) -> None:
    try:
        pend = _mk_dom(calle_status="PENDIENTE")
        items = list_pendientes(slice=None)
        ids = {i["domicilio_id"] for i in items}
        assert pend.id in ids
        assert "slice" not in items[0]
    finally:
        db.session.rollback()


def test_gestion_domicilios_query_rejects_bad_status() -> None:
    with pytest.raises(ValidationError):
        GestionDomiciliosQuery(status_operativo="invalido")  # type: ignore[arg-type]
