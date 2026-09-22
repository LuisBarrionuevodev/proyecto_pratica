"""
REL-DISTRITO-BACKFILL.1 — backfill controlado de distrito en domicilios geo OK.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
    backfill_distrito_for_domicilio_if_needed,
    count_domicilios_geo_ok_sin_distrito,
    run_backfill_domicilios_geo_ok_sin_distrito,
)
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_operativo_to_row
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.list_service import listar_relevamientos_operativos_con_filtros
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.models import Domicilio, DomicilioGeocode, Distrito, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq

_LAT = -26.8166506
_LNG = -65.233452


def _distrito_test() -> Distrito:
    dist = Distrito.query.order_by(Distrito.id.asc()).first()
    if dist is None:
        pytest.skip("Se requiere al menos un distrito en la BD de test")
    return dist


def _set_geocode(
    domicilio_id: int,
    *,
    geo_status: str = "OK",
    lat: Decimal | None = Decimal(str(_LAT)),
    lng: Decimal | None = Decimal(str(_LNG)),
    source: str = "MANUAL",
) -> DomicilioGeocode:
    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id, deleted_at=None).first()
    if geo is None:
        geo = DomicilioGeocode(domicilio_id=domicilio_id)
        db.session.add(geo)
    geo.geo_status = geo_status
    geo.lat = lat
    geo.lng = lng
    geo.source = source
    db.session.flush()
    return geo


def _mk_candidato(
    *,
    distrito_id: int | None = None,
    geo_status: str = "OK",
    lat: Decimal | None = Decimal(str(_LAT)),
    lng: Decimal | None = Decimal(str(_LNG)),
) -> Domicilio:
    dom = Domicilio(calle=uniq("BackfillDist"), numero="100", distrito_id=distrito_id)
    db.session.add(dom)
    db.session.flush()
    _set_geocode(dom.id, geo_status=geo_status, lat=lat, lng=lng)
    db.session.commit()
    return dom


def _patch_resolve(monkeypatch: pytest.MonkeyPatch, resolver) -> None:
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.resolve_distrito_id",
        resolver,
    )


def test_candidato_valido_asigna_distrito(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_candidato(distrito_id=None)

    summary = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))

    dom_ref = db.session.get(Domicilio, dom.id)
    assert dom_ref is not None
    assert dom_ref.distrito_id == dist.id
    assert summary.assigned == 1
    assert summary.despues_restantes == 0


def test_ya_tiene_distrito_no_es_candidato(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_candidato(distrito_id=dist.id)

    assert count_domicilios_geo_ok_sin_distrito(domicilio_id=int(dom.id)) == 0
    summary = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))
    assert summary.candidatos == 0
    assert summary.assigned == 0
    assert backfill_distrito_for_domicilio_if_needed(int(dom.id)) is False


def test_geo_status_no_ok_no_es_candidato(app_ctx) -> None:
    dom = _mk_candidato(distrito_id=None, geo_status="GEO_PENDING")
    assert count_domicilios_geo_ok_sin_distrito(domicilio_id=int(dom.id)) == 0


def test_coords_null_no_es_candidato(app_ctx) -> None:
    dom = _mk_candidato(distrito_id=None, lat=None, lng=None)
    assert count_domicilios_geo_ok_sin_distrito(domicilio_id=int(dom.id)) == 0


def test_resolver_sin_match_permance_null(app_ctx, monkeypatch) -> None:
    _patch_resolve(monkeypatch, lambda _lat, _lng: None)
    dom = _mk_candidato(distrito_id=None)

    summary = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))

    dom_ref = db.session.get(Domicilio, dom.id)
    assert dom_ref is not None
    assert dom_ref.distrito_id is None
    assert summary.no_match == 1
    assert summary.assigned == 0


def test_error_individual_no_aborta_lote(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom_ok = _mk_candidato(distrito_id=None)
    dom_err = _mk_candidato(distrito_id=None)
    original_backfill = backfill_distrito_for_domicilio_if_needed

    def _backfill_con_falla_puntual(domicilio_id: int) -> bool:
        if int(domicilio_id) == int(dom_err.id):
            raise RuntimeError("fallo puntual")
        return original_backfill(int(domicilio_id))

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.backfill_distrito_for_domicilio_if_needed",
        _backfill_con_falla_puntual,
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service._fetch_candidatos_geo_ok_sin_distrito",
        lambda **kwargs: [
            (int(dom_ok.id), float(_LAT), float(_LNG)),
            (int(dom_err.id), float(_LAT), float(_LNG)),
        ],
    )
    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.count_domicilios_geo_ok_sin_distrito",
        lambda **kwargs: 2,
    )

    summary = run_backfill_domicilios_geo_ok_sin_distrito(apply=True)

    ok_ref = db.session.get(Domicilio, dom_ok.id)
    err_ref = db.session.get(Domicilio, dom_err.id)
    assert ok_ref is not None and ok_ref.distrito_id == dist.id
    assert err_ref is not None and err_ref.distrito_id is None
    assert summary.errors == 1
    assert summary.assigned == 1
    assert summary.candidatos == 2
    assert int(dom_err.id) in {row["domicilio_id"] for row in summary.error_details}


def test_dry_run_no_persiste(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_candidato(distrito_id=None)

    summary = run_backfill_domicilios_geo_ok_sin_distrito(
        apply=False,
        domicilio_id=int(dom.id),
    )

    dom_ref = db.session.get(Domicilio, dom.id)
    assert dom_ref is not None
    assert dom_ref.distrito_id is None
    assert summary.assigned == 1
    assert summary.despues_restantes == summary.antes_geo_ok_sin_distrito


def test_apply_persiste(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_candidato(distrito_id=None)

    run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))

    dom_ref = db.session.get(Domicilio, dom.id)
    assert dom_ref is not None
    assert dom_ref.distrito_id == dist.id


def test_segunda_ejecucion_idempotente(app_ctx, monkeypatch) -> None:
    dist = _distrito_test()
    _patch_resolve(monkeypatch, lambda _lat, _lng: dist.id)
    dom = _mk_candidato(distrito_id=None)

    first = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))
    second = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=int(dom.id))

    assert first.assigned == 1
    assert second.candidatos == 0
    assert second.assigned == 0
    dom_ref = db.session.get(Domicilio, dom.id)
    assert dom_ref is not None
    assert dom_ref.distrito_id == dist.id


def test_caso_control_13871_gestion_operativa(app_ctx, monkeypatch) -> None:
    """
    Caso REL-DISTRITO.2C: domicilio 13871 / relevamiento 4387 (si existen en BD).
    """
    dom = db.session.get(Domicilio, 13871)
    rel = db.session.get(Relevamiento, 4387)
    if dom is None or rel is None:
        pytest.skip("Caso control 4387/13871 no presente en BD de test")

    dist = db.session.get(Distrito, 4)
    if dist is None:
        pytest.skip("Distrito id=4 no presente en BD de test")

    dom.distrito_id = None
    _set_geocode(
        13871,
        geo_status="OK",
        lat=Decimal(str(_LAT)),
        lng=Decimal(str(_LNG)),
        source="MANUAL",
    )
    ini = get_or_create_iniciador_from_relevamiento(rel, actor_user_id=1)
    ini.estado_iniciador = "PENDIENTE"
    db.session.add_all([dom, rel, ini])
    db.session.commit()

    monkeypatch.setattr(
        "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.resolve_distrito_id",
        lambda _lat, _lng: 4,
    )

    summary = run_backfill_domicilios_geo_ok_sin_distrito(apply=True, domicilio_id=13871)
    assert summary.assigned == 1

    dom_ref = db.session.get(Domicilio, 13871)
    assert dom_ref is not None
    assert dom_ref.distrito_id == 4

    filters = RelevamientosListFilters.model_validate(
        {"desde": "2020-01-01", "hasta": "2099-12-31", "page": 1, "page_size": 500}
    )
    result = listar_relevamientos_operativos_con_filtros(filters)
    row = None
    for r, ini_row in result["items"]:
        if int(r.id) == 4387:
            row = relevamiento_operativo_to_row(r, ini_row.id, ini_row.estado_iniciador)
            break
    assert row is not None
    assert row["distrito_id"] == 4
    assert row["distrito_codigo"] == dist.codigo
    assert row["distrito_nombre"] == dist.nombre
    assert row["distrito_mostrar"] == dist.nombre
