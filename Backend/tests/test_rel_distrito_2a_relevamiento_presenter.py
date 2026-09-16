"""
REL-DISTRITO.2A — distrito_mostrar en presenters de gestión de relevamientos.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.database import db
from app.domains.domicilios.utils.domicilio_distrito_display import (
    domicilio_distrito_gestion_fields,
    domicilio_geocode_valido_para_distrito,
)
from app.domains.relevamientos.presenters.relevamiento_presenter import (
    relevamiento_operativo_to_row,
    relevamiento_to_row,
)
from app.domains.relevamientos.services.list_service import _relevamiento_gestion_list_query_options
from app.models import Domicilio, DomicilioGeocode, Relevamiento, Rubro


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_geo(
    *,
    geo_status: str,
    lat: Decimal | None = None,
    lng: Decimal | None = None,
) -> DomicilioGeocode:
    return DomicilioGeocode(
        domicilio_id=1,
        geo_status=geo_status,
        lat=lat,
        lng=lng,
        source="MANUAL",
    )


def _mk_dom_con_relaciones(
    *,
    distrito_id: int | None,
    distrito: object | None,
    geocode: DomicilioGeocode | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=101,
        distrito_id=distrito_id,
        distrito=distrito,
        geocode=geocode,
        calle="Maipú",
        calle_raw=None,
        numero="100",
        calle_normalizada=None,
        calle_norm_status=None,
        calle_norm_score=None,
        calle_catalogo_id=None,
        numero_tipo="NUMERO",
        esquina_raw=None,
        esquina_normalizada=None,
        esquina_catalogo_id=None,
        esquina_norm_status=None,
        esquina_norm_score=None,
    )


def _mk_rel(dom: object) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        fecha=date(2026, 5, 10),
        relevadores=[],
        inspector=None,
        domicilio=dom,
        rubro=SimpleNamespace(nombre="Panadería"),
        nombre_fantasia=None,
        angulo_esquina=None,
        turno_carga=None,
        esta_abierto=None,
    )


def test_a_geo_ok_coords_distrito_muestra_nombre() -> None:
    dist = SimpleNamespace(id=1, codigo=1, nombre="Distrito 1")
    geo = _mk_geo(
        geo_status="OK",
        lat=Decimal("-26.8241000"),
        lng=Decimal("-65.2226000"),
    )
    dom = _mk_dom_con_relaciones(distrito_id=1, distrito=dist, geocode=geo)
    fields = domicilio_distrito_gestion_fields(dom)  # type: ignore[arg-type]
    assert fields["distrito_id"] == 1
    assert fields["distrito_codigo"] == 1
    assert fields["distrito_nombre"] == "Distrito 1"
    assert fields["distrito_mostrar"] == "Distrito 1"

    row = relevamiento_to_row(_mk_rel(dom))  # type: ignore[arg-type]
    assert row["distrito_mostrar"] == "Distrito 1"
    operativo = relevamiento_operativo_to_row(_mk_rel(dom), iniciador_id=99, iniciador_estado="PENDIENTE")  # type: ignore[arg-type]
    assert operativo["distrito_mostrar"] == "Distrito 1"


def test_b_geo_ok_coords_distrito_null_no_muestra() -> None:
    geo = _mk_geo(
        geo_status="OK",
        lat=Decimal("-26.8241000"),
        lng=Decimal("-65.2226000"),
    )
    dom = _mk_dom_con_relaciones(distrito_id=None, distrito=None, geocode=geo)
    fields = domicilio_distrito_gestion_fields(dom)  # type: ignore[arg-type]
    assert fields["distrito_id"] is None
    assert fields["distrito_mostrar"] is None


def test_c_geo_pending_con_distrito_no_muestra() -> None:
    dist = SimpleNamespace(id=2, codigo=2, nombre="Distrito 2")
    geo = _mk_geo(
        geo_status="PENDING",
        lat=Decimal("-26.8241000"),
        lng=Decimal("-65.2226000"),
    )
    dom = _mk_dom_con_relaciones(distrito_id=2, distrito=dist, geocode=geo)
    fields = domicilio_distrito_gestion_fields(dom)  # type: ignore[arg-type]
    assert fields["distrito_id"] == 2
    assert fields["distrito_mostrar"] is None


def test_d_geo_ok_sin_coords_no_muestra() -> None:
    dist = SimpleNamespace(id=3, codigo=3, nombre="Distrito 3")
    geo = _mk_geo(geo_status="OK", lat=None, lng=None)
    dom = _mk_dom_con_relaciones(distrito_id=3, distrito=dist, geocode=geo)
    fields = domicilio_distrito_gestion_fields(dom)  # type: ignore[arg-type]
    assert fields["distrito_id"] == 3
    assert fields["distrito_mostrar"] is None
    assert domicilio_geocode_valido_para_distrito(geo) is False


def test_e_relevamiento_sin_geocode_no_rompe_presenter(app_ctx) -> None:
    dom = Domicilio(calle=f"RelDist2a_{_unique_num()}", numero="100", distrito_id=None)
    db.session.add(dom)
    db.session.flush()
    rub = Rubro(nombre=f"RubRelDist2a_{_unique_num()}")
    db.session.add(rub)
    db.session.flush()
    rel = Relevamiento(
        fecha=date(2026, 5, 10),
        mes=5,
        anio=2026,
        domicilio_id=dom.id,
        rubro_id=rub.id,
    )
    db.session.add(rel)
    db.session.flush()

    row = relevamiento_to_row(rel)
    assert row["distrito_mostrar"] is None
    assert row["distrito_id"] is None
    assert row["distrito_codigo"] is None
    assert row["distrito_nombre"] is None


def test_f_geocode_heredado_valido_muestra_distrito() -> None:
    """Simula domicilio con geocode+distrito ya persistidos (p. ej. herencia COW)."""
    dist = SimpleNamespace(id=9, codigo=7, nombre="Distrito heredado")
    geo = _mk_geo(
        geo_status="OK",
        lat=Decimal("-26.8300000"),
        lng=Decimal("-65.2100000"),
    )
    dom = _mk_dom_con_relaciones(distrito_id=9, distrito=dist, geocode=geo)
    row = relevamiento_to_row(_mk_rel(dom))  # type: ignore[arg-type]
    assert row["distrito_mostrar"] == "Distrito heredado"
    assert row["distrito_codigo"] == 7


def test_presenter_sin_domicilio_no_rompe() -> None:
    rel = _mk_rel(None)
    row = relevamiento_to_row(rel)  # type: ignore[arg-type]
    assert row["distrito_mostrar"] is None


def test_list_service_declara_eager_loading_domicilio_distrito_geocode() -> None:
    from pathlib import Path

    opts = _relevamiento_gestion_list_query_options()
    assert len(opts) == 4
    src = Path(__file__).resolve().parents[1].joinpath(
        "app/domains/relevamientos/services/list_service.py"
    ).read_text(encoding="utf-8")
    assert "joinedload(Relevamiento.domicilio).joinedload(Domicilio.distrito)" in src
    assert "joinedload(Relevamiento.domicilio).joinedload(Domicilio.geocode)" in src
    assert "listar_relevamientos_operativos_con_filtros" in src
    assert "listar_relevamientos_realizados_actuacion_completada_con_filtros" in src
    assert "_relevamiento_gestion_list_query_options()" in src
