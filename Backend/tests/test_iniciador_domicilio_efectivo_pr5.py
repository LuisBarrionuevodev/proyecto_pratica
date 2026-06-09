"""
PR5 — Fuente efectiva unificada de domicilio/geocode/distrito.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _map_point_desde_iniciador_backlog,
    count_mapa_operativo_pendientes_cola,
)
from app.domains.rutas_trabajo.presenters.ruta_presenters import iniciador_pendiente_to_row
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    DomicilioEfectivoResult,
    resolve_domicilio_efectivo_para_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Notificacion,
    OrdenTrabajo,
    Relevamiento,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"pr5_{_unique_num()}",
        email=f"pr5_{_unique_num()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_iniciador_con_domicilio_valido_usa_iniciador(app_ctx) -> None:
    try:
        dom = Domicilio(calle=f"IniOK{_unique_num()}", numero="1")
        db.session.add(dom)
        db.session.flush()
        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini)
        assert ef.domicilio_id == dom.id
        assert ef.source == "iniciador"
    finally:
        db.session.rollback()


def test_sin_domicilio_ini_recupera_desde_relevamiento(app_ctx) -> None:
    try:
        dom_orig = Domicilio(calle=f"RelO{_unique_num()}", numero="2")
        dom_ini = Domicilio(calle=f"IniViejo{_unique_num()}", numero="3")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today(),
            mes=6,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom_orig.id,
            rubro_id=1,
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini)
        assert ef.domicilio_id == dom_orig.id
        assert ef.source == "relevamiento"
        assert ef.desalineado_con_origen is True
    finally:
        db.session.rollback()


def test_notificacion_recupera_desde_actuacion_origen(app_ctx) -> None:
    try:
        dom_orig = Domicilio(calle=f"NotO{_unique_num()}", numero="4")
        dom_ini = Domicilio(calle=f"NotV{_unique_num()}", numero="5")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()

        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(noti)
        db.session.flush()

        act = Actuaciones(
            fecha=date.today(),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom_orig.id,
            notificacion_id=noti.id,
        )
        db.session.add(act)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            notificacion_id=noti.id,
            actuacion_id=act.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini)
        assert ef.domicilio_id == dom_orig.id
        assert ef.source in ("actuacion", "notificacion")
    finally:
        db.session.rollback()


def test_oficio_recupera_desde_actuacion(app_ctx) -> None:
    try:
        dom_orig = Domicilio(calle=f"OfO{_unique_num()}", numero="6")
        dom_ini = Domicilio(calle=f"OfV{_unique_num()}", numero="7")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()

        act = Actuaciones(
            fecha=date.today(),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom_orig.id,
        )
        db.session.add(act)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            actuacion_id=act.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini)
        assert ef.domicilio_id == dom_orig.id
        assert ef.source == "actuacion"
    finally:
        db.session.rollback()


def test_distrito_desde_origen_con_geocode(app_ctx, monkeypatch) -> None:
    try:
        dist = Distrito.query.order_by(Distrito.id.asc()).first()
        if not dist:
            pytest.skip("Sin distritos en BD")

        dom_orig = Domicilio(calle=f"DistO{_unique_num()}", numero="8", distrito_id=None)
        dom_ini = Domicilio(calle=f"DistV{_unique_num()}", numero="9")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom_orig.id,
                lat=-26.8241,
                lng=-65.2226,
                geo_status="OK",
            )
        )
        db.session.flush()

        monkeypatch.setattr(
            "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.resolve_distrito_id",
            lambda _lat, _lng: dist.id,
        )

        rel = Relevamiento(
            fecha=date.today(),
            mes=6,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom_orig.id,
            rubro_id=1,
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True)
        dom_ref = db.session.get(Domicilio, ef.domicilio_id)
        assert dom_ref is not None
        assert dom_ref.distrito_id == dist.id
        assert ef.has_distrito is True
    finally:
        db.session.rollback()


def test_sin_origen_ni_domicilio_queda_none(app_ctx) -> None:
    try:
        dom = Domicilio(calle=f"Solo{_unique_num()}", numero="0")
        db.session.add(dom)
        db.session.flush()
        dom.deleted_at = date.today()
        db.session.add(dom)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ef = resolve_domicilio_efectivo_para_iniciador(ini)
        assert ef.domicilio_id is None
        assert ef.source == "none"
    finally:
        db.session.rollback()


def test_no_recalcula_geocode(app_ctx, monkeypatch) -> None:
    try:
        dom = Domicilio(calle=f"Geo{_unique_num()}", numero="11")
        db.session.add(dom)
        db.session.flush()
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
                lat=-26.82,
                lng=-65.22,
                geo_status="OK",
                addr_hash="pr5",
            )
        )
        db.session.flush()
        count_before = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).count()

        mock_on = MagicMock()
        monkeypatch.setattr(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
            mock_on,
        )

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        resolve_domicilio_efectivo_para_iniciador(ini, apply_backfill=True)
        mock_on.assert_not_called()
        assert DomicilioGeocode.query.filter_by(domicilio_id=dom.id).count() == count_before
    finally:
        db.session.rollback()


def test_mapa_backlog_usa_domicilio_efectivo_con_distrito(app_ctx) -> None:
    try:
        dist = Distrito.query.order_by(Distrito.id.asc()).first()
        if not dist:
            pytest.skip("Sin distritos")

        dom_orig = Domicilio(calle=f"MapO{_unique_num()}", numero="12", distrito_id=dist.id)
        dom_ini = Domicilio(calle=f"MapV{_unique_num()}", numero="13")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()
        db.session.add(
            DomicilioGeocode(domicilio_id=dom_orig.id, lat=-26.8241, lng=-65.2226, geo_status="OK")
        )
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today() - timedelta(days=1),
            mes=6,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom_orig.id,
            rubro_id=1,
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today() - timedelta(days=1),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        pt = _map_point_desde_iniciador_backlog(ini, distrito_id=dist.id)
        assert pt is not None
        assert pt["domicilio_id"] == dom_orig.id
        assert pt["distrito_id"] == dist.id

        count = count_mapa_operativo_pendientes_cola(
            desde=(date.today() - timedelta(days=2)).isoformat(),
            hasta=date.today().isoformat(),
            distrito_id=dist.id,
            tipo="RELEVAMIENTOS",
        )
        assert count >= 1
    finally:
        db.session.rollback()


def test_presenter_planificacion_usa_domicilio_efectivo(app_ctx) -> None:
    try:
        dom_orig = Domicilio(calle=f"PresO{_unique_num()}", numero="14")
        dom_ini = Domicilio(calle=f"PresV{_unique_num()}", numero="15")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()

        rel = Relevamiento(
            fecha=date.today(),
            mes=6,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom_orig.id,
            rubro_id=1,
        )
        db.session.add(rel)
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["domicilio"]["id"] == dom_orig.id
    finally:
        db.session.rollback()


def test_cumplido_no_sincroniza_en_try_sync(app_ctx) -> None:
    try:
        dom_orig = Domicilio(calle=f"HistO{_unique_num()}", numero="16")
        dom_ini = Domicilio(calle=f"HistV{_unique_num()}", numero="17")
        db.session.add_all([dom_orig, dom_ini])
        db.session.flush()

        u = _ensure_user()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_ini.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        resolve_domicilio_efectivo_para_iniciador(ini, try_sync=True)
        assert ini.domicilio_id == dom_ini.id
    finally:
        db.session.rollback()
