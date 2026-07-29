"""
PR7.12c — Completar Trabajo: calle explícita ESQUINA→NUMERO, geocode heredado sin re-geocode,
dos iniciadores misma intersección, derivados Notificación/Comprobación usan domicilio actuación.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import joinedload

from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, uniq_ruta_numero

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import ensure_geocode_row
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    compute_addr_hash,
    on_domicilio_changed,
)
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
    Motivo,
    Notificacion,
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
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


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


def _set_geocode_ok(domicilio_id: int, *, lat: str = "-26.8300000", lng: str = "-65.2100000") -> None:
    dom = db.session.get(Domicilio, int(domicilio_id))
    assert dom is not None
    geo = ensure_geocode_row(int(domicilio_id))
    geo.lat = Decimal(lat)
    geo.lng = Decimal(lng)
    geo.geo_status = "OK"
    geo.provider = "TEST"
    geo.addr_hash = compute_addr_hash(dom)
    geo.source = "AUTO"
    db.session.add(geo)
    db.session.flush()


def _crear_relevamiento_san_juan_maipu(
    *,
    rubro: Rubro,
    angulo: str,
    fantasia: str,
    calle: str | None = None,
) -> Relevamiento:
    ins = _inspector()
    calle_eff = calle or _uniq("SanJuanMaipu")
    return crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-15",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": calle_eff, "numero": "y Maipu", "numero_tipo": "ESQUINA"},
            "rubro_nombre": rubro.nombre,
            "nombre_fantasia": fantasia,
            "angulo_esquina": angulo,
        }
    )


def _setup_ruta_publicada(ini: IniciadorRuta) -> RutaItem:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u is None:
        pytest.skip("Se requiere usuario activo")
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR712c", estado="ACTIVO")
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


def _cerrar_item(
    item_id: int,
    payload: dict,
    *,
    patch_geocode_hook: bool = True,
) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    if patch_geocode_hook:
        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
            wraps=on_domicilio_changed,
        ) as geo_hook:
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item_id,
                payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
                ejecutado_por_user_id=u.id,
            )
            assert geo_hook.call_count == 0, "copy-on-write no debe disparar on_domicilio_changed"
    else:
        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            cerrar_completar_trabajo_por_ruta_item(
                ruta_item_id=item_id,
                payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
                ejecutado_por_user_id=u.id,
            )


def test_pr712c_completar_esquina_a_numero_usa_calle_payload(
    app_ctx, require_pr72_migration
) -> None:
    """San Juan y Maipú → Maipú 500: calle del payload, no San Juan."""
    rub = Rubro(nombre=_uniq("Carn712c"))
    db.session.add(rub)
    db.session.flush()
    try:
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Carnicería")
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini and rel.domicilio_id
        dom_origen_id = rel.domicilio_id
        item = _setup_ruta_publicada(ini)

        _cerrar_item(
            item.id,
            {
                "calle": "Maipu",
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub.nombre,
            },
        )

        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=item.actuacion_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        dom_origen = db.session.get(Domicilio, dom_origen_id)
        rel_db = db.session.get(Relevamiento, rel.id)
        assert act and act.domicilio and dom_origen and rel_db
        assert act.domicilio_id != dom_origen_id
        assert act.domicilio.calle == "Maipu"
        assert act.domicilio.numero == "500"
        assert act.domicilio.numero_tipo == "NUMERO"
        assert "San Juan" not in (act.domicilio.calle or "")
        assert rel_db.domicilio_id == dom_origen_id
        assert dom_origen.numero_tipo == "ESQUINA"
    finally:
        db.session.rollback()


def test_pr712c_no_dispara_geocode_y_hereda_origen(app_ctx, require_pr72_migration) -> None:
    try:
        rub = Rubro(nombre=_uniq("Verd712c"))
        db.session.add(rub)
        db.session.flush()
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="SE", fantasia="Verdulería")
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini and rel.domicilio_id
        _set_geocode_ok(rel.domicilio_id, lat="-26.1111111", lng="-65.2222222")
        geo_origen_antes = DomicilioGeocode.query.filter_by(domicilio_id=rel.domicilio_id).first()
        assert geo_origen_antes and geo_origen_antes.geo_status == "OK"

        item = _setup_ruta_publicada(ini)
        _cerrar_item(
            item.id,
            {
                "calle": "Maipu",
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub.nombre,
            },
            patch_geocode_hook=True,
        )

        db.session.expunge_all()
        act = Actuaciones.query.filter_by(id=item.actuacion_id).first()
        assert act and act.domicilio_id != rel.domicilio_id
        geo_nuevo = DomicilioGeocode.query.filter_by(domicilio_id=act.domicilio_id).first()
        geo_origen = DomicilioGeocode.query.filter_by(domicilio_id=rel.domicilio_id).first()
        assert geo_nuevo and geo_origen
        assert geo_nuevo.geo_status == "OK"
        assert geo_nuevo.geo_status not in ("PENDING", "GEO_PENDING", "NORM_PENDING")
        assert float(geo_nuevo.lat) == pytest.approx(float(geo_origen.lat))
        assert float(geo_nuevo.lng) == pytest.approx(float(geo_origen.lng))
        assert geo_origen.geo_status == "OK"
    finally:
        db.session.rollback()


def test_pr712c_dos_iniciadores_misma_interseccion_dos_domicilios_reales(
    app_ctx, require_pr72_migration
) -> None:
    try:
        rub_a = Rubro(nombre=_uniq("Carn712cB"))
        rub_b = Rubro(nombre=_uniq("Verd712cB"))
        db.session.add_all([rub_a, rub_b])
        db.session.flush()
        calle_compartida = _uniq("SanJuanMaipu")
        rel_a = _crear_relevamiento_san_juan_maipu(
            rubro=rub_a, angulo="NE", fantasia="Carnicería", calle=calle_compartida
        )
        rel_b = _crear_relevamiento_san_juan_maipu(
            rubro=rub_b, angulo="SE", fantasia="Verdulería", calle=calle_compartida
        )
        assert rel_a.domicilio_id == rel_b.domicilio_id
        dom_esquina_id = rel_a.domicilio_id
        _set_geocode_ok(dom_esquina_id)

        ini_a = IniciadorRuta.query.filter_by(relevamiento_id=rel_a.id, deleted_at=None).first()
        ini_b = IniciadorRuta.query.filter_by(relevamiento_id=rel_b.id, deleted_at=None).first()
        assert ini_a and ini_b
        ini_a_id = ini_a.id
        ini_b_id = ini_b.id
        rel_a_id = rel_a.id
        rel_b_id = rel_b.id

        item_a = _setup_ruta_publicada(ini_a)
        act_a_id = int(item_a.actuacion_id)
        _cerrar_item(
            item_a.id,
            {
                "calle": "Maipu",
                "numero": "500",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub_a.nombre,
            },
        )

        item_b = _setup_ruta_publicada(ini_b)
        act_b_id = int(item_b.actuacion_id)
        calle_san_juan = db.session.get(Domicilio, dom_esquina_id).calle
        _cerrar_item(
            item_b.id,
            {
                "calle": calle_san_juan,
                "numero": "1000",
                "numero_tipo": "NUMERO",
                "rubro_nombre": rub_b.nombre,
            },
        )

        db.session.expunge_all()
        act_a = (
            Actuaciones.query.filter_by(id=act_a_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        act_b = (
            Actuaciones.query.filter_by(id=act_b_id)
            .options(joinedload(Actuaciones.domicilio))
            .first()
        )
        ini_a_db = db.session.get(IniciadorRuta, ini_a_id)
        ini_b_db = db.session.get(IniciadorRuta, ini_b_id)
        rel_a_db = db.session.get(Relevamiento, rel_a_id)
        rel_b_db = db.session.get(Relevamiento, rel_b_id)
        dom_origen = db.session.get(Domicilio, dom_esquina_id)

        assert act_a and act_b and act_a.domicilio and act_b.domicilio
        assert act_a.domicilio.calle == "Maipu"
        assert act_a.domicilio.numero == "500"
        assert act_b.domicilio.calle == calle_san_juan
        assert act_b.domicilio.numero == "1000"
        assert act_a.domicilio_id != act_b.domicilio_id != dom_esquina_id
        assert ini_a_db.domicilio_id == act_a.domicilio_id
        assert ini_b_db.domicilio_id == act_b.domicilio_id
        assert rel_a_db.domicilio_id == dom_esquina_id
        assert rel_b_db.domicilio_id == dom_esquina_id
        assert dom_origen.numero_tipo == "ESQUINA"
    finally:
        db.session.rollback()


def test_pr712c_notificacion_derivada_usa_domicilio_actuacion(
    app_ctx, require_pr72_migration
) -> None:
    try:
        rub = Rubro(nombre=_uniq("Notif712c"))
        db.session.add(rub)
        db.session.flush()
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="NE", fantasia="Local")
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini
        item = _setup_ruta_publicada(ini)

        motivo = Motivo.query.first()
        if motivo is None:
            pytest.skip("Se requiere al menos un motivo en catálogo")
        acta_notif = _unique_num()
        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            _cerrar_item(
                item.id,
                {
                    "calle": "Maipu",
                    "numero": "500",
                    "numero_tipo": "NUMERO",
                    "rubro_nombre": rub.nombre,
                    "acta_notificacion_num": acta_notif,
                    "notificacion_motivo_1": motivo.nombre,
                },
                patch_geocode_hook=False,
            )

        act_id = int(item.actuacion_id)
        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=act_id)
            .options(joinedload(Actuaciones.domicilio), joinedload(Actuaciones.notificacion))
            .first()
        )
        assert act and act.domicilio and act.notificacion_id
        assert act.domicilio.calle == "Maipu"
        assert act.domicilio.numero == "500"

        noti = db.session.get(Notificacion, act.notificacion_id)
        assert noti is not None
        noti.fecha_vencimiento = date.today() - timedelta(days=1)
        db.session.add(noti)
        db.session.commit()

        sync_iniciadores_reinspeccion_notificacion()

        ini_der = (
            IniciadorRuta.query.filter(
                IniciadorRuta.notificacion_id == noti.id,
                IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
                IniciadorRuta.deleted_at.is_(None),
            )
            .first()
        )
        assert ini_der is not None
        assert ini_der.domicilio_id == act.domicilio_id
        dom_der = db.session.get(Domicilio, ini_der.domicilio_id)
        assert dom_der is not None
        assert dom_der.calle == "Maipu"
        assert dom_der.numero == "500"
    finally:
        db.session.rollback()


def test_pr712c_comprobacion_derivada_usa_domicilio_actuacion(
    app_ctx, require_pr72_migration
) -> None:
    """Comprobación en actuación: domicilio real/legal queda en act.domicilio (base para derivados)."""
    try:
        rub = Rubro(nombre=_uniq("Comp712c"))
        db.session.add(rub)
        db.session.flush()
        rel = _crear_relevamiento_san_juan_maipu(rubro=rub, angulo="SO", fantasia="Kiosco")
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
        assert ini
        item = _setup_ruta_publicada(ini)

        with patch(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
        ):
            _cerrar_item(
                item.id,
                {
                    "calle": "Maipu",
                    "numero": "500",
                    "numero_tipo": "NUMERO",
                    "rubro_nombre": rub.nombre,
                    "acta_comprobacion_num": _unique_num(),
                    "comprobacion_motivo": "Incumplimiento",
                },
                patch_geocode_hook=False,
            )

        db.session.expunge_all()
        act = (
            Actuaciones.query.filter_by(id=item.actuacion_id)
            .options(
                joinedload(Actuaciones.domicilio),
                joinedload(Actuaciones.comprobacion),
            )
            .first()
        )
        assert act and act.domicilio and act.comprobacion_id
        assert act.domicilio.calle == "Maipu"
        assert act.domicilio.numero == "500"
        assert act.domicilio_id != rel.domicilio_id
        rel_db = db.session.get(Relevamiento, rel.id)
        assert rel_db.domicilio_id == rel.domicilio_id
    finally:
        db.session.rollback()
