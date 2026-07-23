"""
PR7.12 — Copy-on-write de domicilio real en Completar Trabajo desde relevamiento.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import ensure_geocode_row
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    Relevamiento,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


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


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere al menos un inspector en catálogo")
    return ins


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return rows[0], rows[1]


def _setup_ruta_publicada_con_item(ini: IniciadorRuta) -> RutaItem:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 12),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR712", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=_unique_num(),
        )
    publicar_ruta_trabajo(ruta_id=ruta.id)
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    return item


def _crear_esquina_dos_iniciadores():
    ins = _inspector()
    rub_a = Rubro(nombre=_uniq("CarnPr712"))
    rub_b = Rubro(nombre=_uniq("VerdPr712"))
    db.session.add_all([rub_a, rub_b])
    db.session.flush()
    calle = _uniq("SanMartinColombres")
    rel_a = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-01",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "y Jose Colombres", "numero_tipo": "ESQUINA"},
            "rubro_nombre": rub_a.nombre,
            "nombre_fantasia": "Local NE",
            "angulo_esquina": "NE",
        }
    )
    rel_b = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-02",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle, "numero": "y Jose Colombres", "numero_tipo": "ESQUINA"},
            "rubro_nombre": rub_b.nombre,
            "nombre_fantasia": "Local SE",
            "angulo_esquina": "SE",
        }
    )
    ini_a = IniciadorRuta.query.filter_by(relevamiento_id=rel_a.id, deleted_at=None).first()
    ini_b = IniciadorRuta.query.filter_by(relevamiento_id=rel_b.id, deleted_at=None).first()
    dom = db.session.get(Domicilio, rel_a.domicilio_id)
    assert ini_a and ini_b and dom
    return rel_a, rel_b, ini_a, ini_b, rub_a, rub_b, dom


def _set_geocode_ok(domicilio_id: int, *, lat: str = "-26.8300000", lng: str = "-65.2100000") -> None:
    geo = ensure_geocode_row(int(domicilio_id))
    geo.lat = Decimal(lat)
    geo.lng = Decimal(lng)
    geo.geo_status = "OK"
    geo.provider = "TEST"
    db.session.add(geo)
    db.session.flush()


def test_pr712_san_martin_y_catamarca_queda_catamarca_1000(app_ctx, require_pr72_migration) -> None:
    """Caso obligatorio: ESQUINA → domicilio real NUMERO con calle del payload."""
    ins = _inspector()
    rub = Rubro(nombre=_uniq("PanPr712"))
    db.session.add(rub)
    db.session.flush()
    calle_esquina = _uniq("SanMartinCatamarca")
    try:
        rel = crear_relevamiento_desde_payload(
            {
                "fecha": "2026-07-10",
                "inspector_nombre": ins.nombre,
                "domicilio": {
                    "calle": calle_esquina,
                    "numero": "y Catamarca",
                    "numero_tipo": "ESQUINA",
                },
                "rubro_nombre": rub.nombre,
            }
        )
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini is not None
        dom_origen_id = rel.domicilio_id
        item = _setup_ruta_publicada_con_item(ini)
        u = User.query.filter(User.is_active.is_(True)).first()
        assert u is not None

        payload = CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "calle": "Catamarca",
                "numero": "1000",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub.nombre,
            }
        )
        assert "nombre_fantasia" not in payload.model_dump(exclude_none=True)
        assert "angulo_esquina" not in payload.model_dump(exclude_none=True)

        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item.id,
                payload=payload,
                ejecutado_por_user_id=u.id,
            )

        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=item.actuacion_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        rel_db = db.session.get(Relevamiento, rel.id)
        dom_origen = db.session.get(Domicilio, dom_origen_id)

        assert act and act.domicilio and rel_db and dom_origen
        assert act.domicilio_id != dom_origen_id
        assert act.domicilio.calle == "Catamarca"
        assert act.domicilio.numero == "1000"
        assert act.domicilio.numero_tipo == "NUMERO"
        assert "San Martin" not in (act.domicilio.calle or "")
        assert rel_db.domicilio_id == dom_origen_id
        assert dom_origen.calle == calle_esquina
        assert dom_origen.numero == "y Catamarca"
    finally:
        db.session.rollback()


def test_pr712_completar_no_muta_otro_iniciador_misma_interseccion(
    app_ctx, require_pr72_migration
) -> None:
    try:
        rel_a, rel_b, ini_a, ini_b, rub_a, _rub_b, dom_esquina = _crear_esquina_dos_iniciadores()
        snap_dom_calle = dom_esquina.calle
        snap_dom_numero = dom_esquina.numero
        snap_ini_b_dom_id = ini_b.domicilio_id
        snap_rel_b_dom_id = rel_b.domicilio_id
        snap_rel_a_dom_id = rel_a.domicilio_id
        ini_a_id = ini_a.id
        ini_b_id = ini_b.id
        rel_a_id = rel_a.id
        rel_b_id = rel_b.id
        dom_esquina_id = dom_esquina.id

        item_a = _setup_ruta_publicada_con_item(ini_a)
        item_a_id = item_a.id
        u = User.query.filter(User.is_active.is_(True)).first()
        assert u is not None

        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item_a_id,
                payload=CompletarTrabajoCierreCompletoIn.model_validate(
                    {
                        "calle": "Jose Colombres",
                        "numero": "800",
                        "numero_tipo": "NUMERO",
                        "rubro_nombre": rub_a.nombre,
                    }
                ),
                ejecutado_por_user_id=u.id,
            )

        db.session.expunge_all()
        item_a_db = db.session.get(RutaItem, item_a_id)
        act_a = (
            Actuaciones.query.filter_by(id=item_a_db.actuacion_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        ini_a_db = db.session.get(IniciadorRuta, ini_a_id)
        ini_b_db = db.session.get(IniciadorRuta, ini_b_id)
        rel_a_db = db.session.get(Relevamiento, rel_a_id)
        rel_b_db = db.session.get(Relevamiento, rel_b_id)
        dom_db = db.session.get(Domicilio, dom_esquina_id)

        assert act_a and act_a.domicilio and ini_a_db and ini_b_db
        assert act_a.domicilio_id != dom_esquina_id
        assert ini_a_db.domicilio_id == act_a.domicilio_id
        assert ini_b_db.domicilio_id == snap_ini_b_dom_id == dom_esquina_id
        assert rel_a_db.domicilio_id == snap_rel_a_dom_id
        assert rel_b_db.domicilio_id == snap_rel_b_dom_id == dom_esquina_id
        assert dom_db.calle == snap_dom_calle
        assert dom_db.numero == snap_dom_numero
    finally:
        db.session.rollback()


def test_pr712_nuevo_domicilio_hereda_geocode_origen(app_ctx, require_pr72_migration) -> None:
    ins = _inspector()
    rub = Rubro(nombre=_uniq("CafePr712"))
    db.session.add(rub)
    db.session.flush()
    try:
        rel = crear_relevamiento_desde_payload(
            {
                "fecha": "2026-07-11",
                "inspector_nombre": ins.nombre,
                "domicilio": {"calle": _uniq("Belgrano"), "numero": "y Mitre", "numero_tipo": "ESQUINA"},
                "rubro_nombre": rub.nombre,
            }
        )
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini and rel.domicilio_id
        _set_geocode_ok(rel.domicilio_id, lat="-26.1111111", lng="-65.2222222")
        geo_origen = DomicilioGeocode.query.filter_by(domicilio_id=rel.domicilio_id).first()
        assert geo_origen and geo_origen.lat is not None

        item = _setup_ruta_publicada_con_item(ini)
        u = User.query.filter(User.is_active.is_(True)).first()
        assert u

        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item.id,
                payload=CompletarTrabajoCierreCompletoIn.model_validate(
                    {
                        "calle": "Mitre",
                        "numero": "450",
                        "numero_tipo": "NUMERO",
                        "rubro_nombre": rub.nombre,
                    }
                ),
                ejecutado_por_user_id=u.id,
            )

        db.session.expunge_all()
        act = Actuaciones.query.filter_by(id=item.actuacion_id).first()
        assert act and act.domicilio_id != rel.domicilio_id
        geo_nuevo = DomicilioGeocode.query.filter_by(domicilio_id=act.domicilio_id).first()
        geo_origen_db = DomicilioGeocode.query.filter_by(domicilio_id=rel.domicilio_id).first()
        assert geo_nuevo and geo_origen_db
        assert float(geo_nuevo.lat) == pytest.approx(float(geo_origen_db.lat))
        assert float(geo_nuevo.lng) == pytest.approx(float(geo_origen_db.lng))
        assert geo_nuevo.geo_status == "OK"
        assert geo_origen_db.geo_status == "OK"
    finally:
        db.session.rollback()


def test_pr712_actuacion_crud_relevamiento_no_muta_domicilio_origen(
    app_ctx, require_pr72_migration
) -> None:
    ins = _inspector()
    rub = Rubro(nombre=_uniq("RotiPr712"))
    db.session.add(rub)
    db.session.flush()
    try:
        calle = _uniq("Rivadavia")
        rel = crear_relevamiento_desde_payload(
            {
                "fecha": "2026-07-12",
                "inspector_nombre": ins.nombre,
                "domicilio": {"calle": calle, "numero": "y San Lorenzo", "numero_tipo": "ESQUINA"},
                "rubro_nombre": rub.nombre,
            }
        )
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini
        item = _setup_ruta_publicada_con_item(ini)
        actuacion_id = int(item.actuacion_id)
        rel_id = rel.id
        dom_origen_id = rel.domicilio_id
        snap_calle = db.session.get(Domicilio, dom_origen_id).calle

        actualizar_actuacion(
            actuacion_id,
            {
                "domicilio": {
                    "calle": "San Lorenzo",
                    "numero": "1200",
                    "numero_tipo": "NUMERO",
                },
                "rubro_nombre": rub.nombre,
                "contribuyente": {"doc_nro": "30111222", "apellido": "Test", "nombre": "CRUD"},
            },
        )

        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=actuacion_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        rel_db = db.session.get(Relevamiento, rel_id)
        dom_origen = db.session.get(Domicilio, dom_origen_id)
        assert act and act.domicilio and rel_db and dom_origen
        assert act.domicilio_id != dom_origen_id
        assert act.domicilio.calle == "San Lorenzo"
        assert act.domicilio.numero == "1200"
        assert rel_db.domicilio_id == dom_origen_id
        assert dom_origen.calle == snap_calle
    finally:
        db.session.rollback()
