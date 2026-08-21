"""OPER-RUTA.7B-HOTFIX — Relevamientos geolocalizados en M4 pendientes-contexto."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.distrito_backfill_service import (
    backfill_distrito_for_domicilio_if_needed,
)
from app.domains.geolocalizacion.geocode.services.distritos_service import resolve_distrito_id
from app.domains.relevamientos.services.relevamiento_iniciador_service import (
    get_or_create_iniciador_from_relevamiento,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.planificacion_service import (
    get_planificacion_pendientes_contexto,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import (
    Distrito,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    Relevamiento,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero, unique_ot_numero

# Coordenadas centrales Tucumán (usadas en otros tests de mapa/distrito).
_LAT = -26.8241
_LNG = -65.2226


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"relhot_{unique_ot_numero()}",
        email=f"relhot_{unique_ot_numero()}@t.local",
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


def _distrito_con_geom() -> Distrito:
    resolved_id = resolve_distrito_id(_LAT, _LNG)
    if resolved_id is None:
        pytest.skip("Coords de test sin match de distrito")
    dist = db.session.get(Distrito, int(resolved_id))
    if not dist or dist.geom is None:
        pytest.skip("Distrito resuelto sin geom en la DB de test")
    return dist


def _mk_relevamiento_geolocalizado(
    user: User,
    *,
    distrito_id_fk: int | None,
    rubro_id: int = 1,
    inspector_id: int = 1,
    iniciador_domicilio_desalineado: bool = False,
) -> tuple[Relevamiento, IniciadorRuta, Domicilio]:
    """Crea relevamiento + geocode OK + iniciador PENDIENTE (patrón producción)."""
    dom_origen = Domicilio(
        calle=f"RelHot_{unique_ot_numero()}",
        numero="900",
        distrito_id=distrito_id_fk,
    )
    dom_ini = None
    if iniciador_domicilio_desalineado:
        dom_ini = Domicilio(calle=f"RelViejo_{unique_ot_numero()}", numero="1")
        db.session.add(dom_ini)
    db.session.add(dom_origen)
    db.session.flush()

    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom_origen.id,
            lat=_LAT,
            lng=_LNG,
            geo_status="OK",
            source="MANUAL",
        )
    )
    db.session.flush()

    rel = Relevamiento(
        fecha=date.today(),
        mes=date.today().month,
        anio=date.today().year,
        inspector_id=inspector_id,
        domicilio_id=dom_origen.id,
        rubro_id=rubro_id,
        created_by_user_id=user.id,
    )
    db.session.add(rel)
    db.session.flush()

    ini = get_or_create_iniciador_from_relevamiento(rel)
    db.session.add(ini)
    if iniciador_domicilio_desalineado and dom_ini is not None:
        ini.domicilio_id = dom_ini.id
    db.session.flush()
    return rel, ini, dom_origen


def _mk_relevamiento_iniciador_sin_backfill_distrito(
    user: User,
    *,
    rubro_id: int = 1,
    inspector_id: int = 1,
) -> tuple[Relevamiento, IniciadorRuta, Domicilio]:
    """Relevamiento geolocalizado con domicilio.distrito_id NULL (sin backfill al crear)."""
    dom_origen = Domicilio(
        calle=f"RelNull_{unique_ot_numero()}",
        numero="901",
        distrito_id=None,
    )
    db.session.add(dom_origen)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom_origen.id,
            lat=_LAT,
            lng=_LNG,
            geo_status="OK",
            source="MANUAL",
        )
    )
    db.session.flush()

    rel = Relevamiento(
        fecha=date.today(),
        mes=date.today().month,
        anio=date.today().year,
        inspector_id=inspector_id,
        domicilio_id=dom_origen.id,
        rubro_id=rubro_id,
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
        domicilio_id=dom_origen.id,
        relevamiento_id=rel.id,
        prioridad=1,
        created_by_user_id=user.id,
    )
    db.session.add(ini)
    db.session.flush()
    assert dom_origen.distrito_id is None
    return rel, ini, dom_origen


def _m4_ids(ruta_id: int, distrito_id: int, *, tipo: str | None = None) -> set[int]:
    items, _ = get_planificacion_pendientes_contexto(
        ruta_id,
        distrito_id=distrito_id,
        tipo=tipo,
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


def test_m4_relevamiento_geolocalizado_libre_aparece(app_ctx) -> None:
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, _dom = _mk_relevamiento_geolocalizado(u, distrito_id_fk=int(dist.id))
    db.session.commit()

    ids = _m4_ids(int(ruta.id), int(dist.id))
    assert int(ini.id) in ids


def test_m4_relevamiento_distrito_fk_null_resuelve_por_geocode(app_ctx) -> None:
    """Regresión 7B: FK NULL + geocode OK debe coincidir con path legacy (backfill/spatial)."""
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, dom = _mk_relevamiento_iniciador_sin_backfill_distrito(u)
    db.session.commit()

    ids = _m4_ids(int(ruta.id), int(dist.id))
    assert int(ini.id) in ids


def test_m4_relevamiento_desalineado_usa_domicilio_origen(app_ctx) -> None:
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, dom_origen = _mk_relevamiento_geolocalizado(
        u,
        distrito_id_fk=int(dist.id),
        iniciador_domicilio_desalineado=True,
    )
    assert ini.domicilio_id != dom_origen.id
    db.session.commit()

    ids = _m4_ids(int(ruta.id), int(dist.id))
    assert int(ini.id) in ids


def test_m4_relevamiento_filtro_tipo(app_ctx) -> None:
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, _dom = _mk_relevamiento_geolocalizado(u, distrito_id_fk=int(dist.id))
    db.session.commit()

    solo_rel = _m4_ids(int(ruta.id), int(dist.id), tipo="RELEVAMIENTO")
    assert int(ini.id) in solo_rel

    solo_den = _m4_ids(int(ruta.id), int(dist.id), tipo="DENUNCIA")
    assert int(ini.id) not in solo_den


def test_m4_relevamiento_en_pool_no_aparece(app_ctx) -> None:
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, _dom = _mk_relevamiento_geolocalizado(u, distrito_id_fk=int(dist.id))
    db.session.commit()

    create_ruta_pool_dia_entry(
        fecha=ruta.fecha,
        turno_id=None,
        usuario_id=int(u.id),
        iniciador_ruta_id=int(ini.id),
        ruta_trabajo_id=int(ruta.id),
    )
    db.session.commit()

    ids = _m4_ids(int(ruta.id), int(dist.id))
    assert int(ini.id) not in ids


def test_m4_relevamiento_en_grupo_borrador_no_aparece(app_ctx) -> None:
    dist = _distrito_con_geom()
    u = _mk_user()
    ruta = _mk_ruta(u)
    _rel, ini, _dom = _mk_relevamiento_geolocalizado(u, distrito_id_fk=int(dist.id))
    ins = Inspector.query.limit(2).all()
    if len(ins) < 2:
        pytest.skip("Se requieren 2 inspectores")
    db.session.commit()

    grupo = create_ruta_grupo(ruta_id=int(ruta.id), nombre="GRelHot", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        inspector_ids=[ins[0].id, ins[1].id],
    )
    assign_iniciadores_to_grupo(
        ruta_id=int(ruta.id),
        grupo_id=int(grupo.id),
        iniciador_ids=[int(ini.id)],
    )
    db.session.commit()

    ids = _m4_ids(int(ruta.id), int(dist.id))
    assert int(ini.id) not in ids


def test_backfill_tras_enrich_persiste_distrito(app_ctx) -> None:
    """Tras lectura M4, el backfill de enrich puede persistir distrito_id."""
    u = _mk_user()
    _rel, _ini, dom = _mk_relevamiento_iniciador_sin_backfill_distrito(u)
    db.session.commit()

    assert backfill_distrito_for_domicilio_if_needed(int(dom.id)) is True
    db.session.commit()
    db.session.refresh(dom)
    assert dom.distrito_id is not None
