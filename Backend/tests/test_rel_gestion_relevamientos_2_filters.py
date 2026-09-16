"""
REL-GESTION-RELEVAMIENTOS.2 — filtros esta_abierto y distrito_id en listados de relevamiento.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from app.database import db
from app.domains.relevamientos.schemas.list_filters import RelevamientosListFilters
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.list_service import (
    listar_relevamientos_operativos_con_filtros,
)
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.models import Domicilio, DomicilioGeocode, Distrito, Relevamiento
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro, uniq


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _distritos_test(min_count: int = 1) -> list[Distrito]:
    rows = Distrito.query.order_by(Distrito.id.asc()).limit(min_count).all()
    if len(rows) < min_count:
        pytest.skip(f"Se requieren al menos {min_count} distritos en la BD de test")
    return rows


def _set_geocode(
    domicilio_id: int,
    *,
    geo_status: str = "OK",
    lat: Decimal | None = Decimal("-26.8241000"),
    lng: Decimal | None = Decimal("-65.2226000"),
) -> None:
    geo = DomicilioGeocode.query.filter_by(domicilio_id=domicilio_id, deleted_at=None).first()
    if geo is None:
        geo = DomicilioGeocode(domicilio_id=domicilio_id)
        db.session.add(geo)
    geo.geo_status = geo_status
    geo.lat = lat
    geo.lng = lng
    geo.source = "MANUAL"
    db.session.flush()


def _mk_operativo(
    *,
    esta_abierto: bool | None,
    distrito: Distrito | None = None,
    geo_status: str = "OK",
    lat: Decimal | None = Decimal("-26.8241000"),
    lng: Decimal | None = Decimal("-65.2226000"),
) -> Relevamiento:
    rev = get_or_create_test_relevador()
    rub = get_test_rubro()
    calle = uniq("GestRel2")
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-06-01",
            "relevadores_nombres": [rev.nombre],
            "domicilio": {"calle": calle, "numero": "100"},
            "rubro_nombre": rub.nombre,
            "esta_abierto": esta_abierto,
        }
    )
    rel.esta_abierto = esta_abierto
    dom = db.session.get(Domicilio, rel.domicilio_id)
    assert dom is not None
    if distrito is not None:
        dom.distrito_id = distrito.id
    _set_geocode(dom.id, geo_status=geo_status, lat=lat, lng=lng)
    ini = get_or_create_iniciador_from_relevamiento(rel)
    ini.estado_iniciador = "PENDIENTE"
    db.session.add_all([rel, dom, ini])
    db.session.commit()
    return rel


def _ids(filters_kwargs: dict) -> set[int]:
    filters = RelevamientosListFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            **filters_kwargs,
        }
    )
    result = listar_relevamientos_operativos_con_filtros(filters)
    return {int(r.id) for r, _ in result["items"]}


def test_esta_abierto_true_solo_abiertos(app_ctx) -> None:
    abierto = _mk_operativo(esta_abierto=True)
    cerrado = _mk_operativo(esta_abierto=False)
    sin_dato = _mk_operativo(esta_abierto=None)

    ids = _ids({"esta_abierto": True})
    assert abierto.id in ids
    assert cerrado.id not in ids
    assert sin_dato.id not in ids


def test_esta_abierto_false_solo_cerrados(app_ctx) -> None:
    abierto = _mk_operativo(esta_abierto=True)
    cerrado = _mk_operativo(esta_abierto=False)

    ids = _ids({"esta_abierto": False})
    assert cerrado.id in ids
    assert abierto.id not in ids


def test_sin_esta_abierto_incluye_ambos(app_ctx) -> None:
    abierto = _mk_operativo(esta_abierto=True)
    cerrado = _mk_operativo(esta_abierto=False)

    ids = _ids({})
    assert abierto.id in ids
    assert cerrado.id in ids


def test_distrito_id_geo_ok_incluido(app_ctx) -> None:
    dist_a, dist_b = _distritos_test(2)
    rel_ok = _mk_operativo(esta_abierto=True, distrito=dist_a)
    otro = _mk_operativo(esta_abierto=True, distrito=dist_b)

    ids = _ids({"distrito_id": dist_a.id})
    assert rel_ok.id in ids
    assert otro.id not in ids


def test_distrito_id_geo_invalido_excluido(app_ctx) -> None:
    dist = _distritos_test(1)[0]
    rel_pending = _mk_operativo(
        esta_abierto=True,
        distrito=dist,
        geo_status="PENDING",
    )
    rel_sin_coords = _mk_operativo(
        esta_abierto=True,
        distrito=dist,
        lat=None,
        lng=None,
    )

    ids = _ids({"distrito_id": dist.id})
    assert rel_pending.id not in ids
    assert rel_sin_coords.id not in ids


def test_filtros_combinados_and(app_ctx) -> None:
    dist_a, dist_b = _distritos_test(2)
    rev = get_or_create_test_relevador()
    match = _mk_operativo(esta_abierto=True, distrito=dist_a)

    otro_dist = _mk_operativo(esta_abierto=False, distrito=dist_a)
    otro_rev = _mk_operativo(esta_abierto=True, distrito=dist_b)

    ids = _ids({"esta_abierto": True, "distrito_id": dist_a.id, "relevador": rev.nombre})
    assert match.id in ids
    assert otro_dist.id not in ids
    assert otro_rev.id not in ids
