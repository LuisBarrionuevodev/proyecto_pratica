"""REL-MAP-CIERRE.5-6 — Fuera de distritos + alineación M2/M4."""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.distritos_service import resolve_distrito_id
from app.domains.rutas_trabajo.services.planificacion_service import (
    get_carga_por_distritos,
    get_planificacion_pendientes_contexto,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import Domicilio, DomicilioGeocode, IniciadorRuta, Relevamiento, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero

_LAT_INSIDE = -26.8241
_LNG_INSIDE = -65.2226
_LAT_OUTSIDE = 10.0
_LNG_OUTSIDE = 10.0


def _mk_user() -> User:
    u = User(
        username=f"outd_{unique_ot_numero()}",
        email=f"outd_{unique_ot_numero()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ruta(user: User) -> RutaTrabajo:
    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=user.id,
    )
    db.session.add(ruta)
    db.session.flush()
    return ruta


def _distrito_inside() -> int:
    resolved = resolve_distrito_id(_LAT_INSIDE, _LNG_INSIDE)
    if resolved is None:
        pytest.skip("Coords inside sin distrito en DB de test")
    return int(resolved)


def _mk_ini_relevamiento(
    user: User,
    *,
    distrito_id_fk: int | None,
    lat: float,
    lng: float,
    geo_status: str = "OK",
    with_geo: bool = True,
) -> IniciadorRuta:
    dom = Domicilio(
        calle=f"OutD_{unique_ot_numero()}",
        numero="100",
        distrito_id=distrito_id_fk,
    )
    db.session.add(dom)
    db.session.flush()
    if with_geo:
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
                lat=lat,
                lng=lng,
                geo_status=geo_status,
                source="MANUAL",
            )
        )
        db.session.flush()
    rel = Relevamiento(
        fecha=date.today(),
        mes=date.today().month,
        anio=date.today().year,
        domicilio_id=dom.id,
        rubro_id=1,
        created_by_user_id=user.id,
    )
    db.session.add(rel)
    db.session.flush()
    ini = IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=rel.fecha,
        anio=rel.anio,
        mes=rel.mes,
        domicilio_id=dom.id,
        relevamiento_id=rel.id,
        prioridad=1,
        created_by_user_id=user.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _m4_distrito_ids(ruta_id: int, distrito_id: int) -> set[int]:
    items, _ = get_planificacion_pendientes_contexto(
        ruta_id,
        distrito_id=distrito_id,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=500,
        orden="prioridad",
    )
    return {int(i.id) for i in items}


def _m4_outside_ids(ruta_id: int) -> set[int]:
    items, _ = get_planificacion_pendientes_contexto(
        ruta_id,
        distrito_id=None,
        scope_outside_districts=True,
        tipo=None,
        prioridad=None,
        prioridad_categoria=None,
        q=None,
        turno_sugerido=None,
        calle_catalogo_id=None,
        page=1,
        per_page=500,
        orden="prioridad",
    )
    return {int(i.id) for i in items}


def test_m4_fk_explicita_aparece_en_distrito(app_ctx) -> None:
    dist = _distrito_inside()
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=dist, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    db.session.commit()
    assert int(ini.id) in _m4_distrito_ids(int(ruta.id), dist)


def test_m4_fk_null_spatial_inside_aparece_en_distrito(app_ctx) -> None:
    dist = _distrito_inside()
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    db.session.commit()
    assert int(ini.id) in _m4_distrito_ids(int(ruta.id), dist)


def test_m4_fk_null_spatial_inside_no_aparece_outside(app_ctx) -> None:
    dist = _distrito_inside()
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    db.session.commit()
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))


def test_m4_fk_null_fuera_aparece_outside(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_OUTSIDE, lng=_LNG_OUTSIDE)
    db.session.commit()
    assert int(ini.id) in _m4_outside_ids(int(ruta.id))


def test_m4_sin_coords_no_outside(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(
        u, distrito_id_fk=None, lat=_LAT_OUTSIDE, lng=_LNG_OUTSIDE, with_geo=False
    )
    db.session.commit()
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))


def test_m4_geo_error_no_outside(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(
        u,
        distrito_id_fk=None,
        lat=_LAT_OUTSIDE,
        lng=_LNG_OUTSIDE,
        geo_status="ERROR",
    )
    db.session.commit()
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))


def test_m4_geo_no_match_no_outside(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(
        u,
        distrito_id_fk=None,
        lat=_LAT_OUTSIDE,
        lng=_LNG_OUTSIDE,
        geo_status="NO_MATCH",
    )
    db.session.commit()
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))


def test_m4_fk_explicita_precede_sobre_outside(app_ctx) -> None:
    dist = _distrito_inside()
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=dist, lat=_LAT_OUTSIDE, lng=_LNG_OUTSIDE)
    db.session.commit()
    assert int(ini.id) in _m4_distrito_ids(int(ruta.id), dist)
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))


def test_m2_cuenta_fk_y_spatial_sin_duplicar(app_ctx) -> None:
    dist = _distrito_inside()
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini_fk = _mk_ini_relevamiento(u, distrito_id_fk=dist, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    ini_sp = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    db.session.commit()

    data = get_carga_por_distritos(int(ruta.id))
    row = next((r for r in data["items"] if r["distrito_id"] == dist), None)
    assert row is not None
    assert row["cantidad"] >= 2
    assert int(ini_fk.id) in _m4_distrito_ids(int(ruta.id), dist)
    assert int(ini_sp.id) in _m4_distrito_ids(int(ruta.id), dist)


def test_m2_outside_districts_count(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini_out = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_OUTSIDE, lng=_LNG_OUTSIDE)
    _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_INSIDE, lng=_LNG_INSIDE)
    db.session.commit()

    data = get_carga_por_distritos(int(ruta.id))
    assert data["outside_districts_count"] >= 1
    assert int(ini_out.id) in _m4_outside_ids(int(ruta.id))


def test_pool_outside_scope_success(app_ctx) -> None:
    u = _mk_user()
    ruta = _mk_ruta(u)
    ini = _mk_ini_relevamiento(u, distrito_id_fk=None, lat=_LAT_OUTSIDE, lng=_LNG_OUTSIDE)
    db.session.commit()
    assert int(ini.id) in _m4_outside_ids(int(ruta.id))

    entry = create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=int(u.id),
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )
    db.session.commit()
    assert entry is not None
    assert int(ini.id) not in _m4_outside_ids(int(ruta.id))
