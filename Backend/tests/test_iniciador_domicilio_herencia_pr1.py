"""
PR1 — Herencia domicilio/geocode/distrito al crear iniciadores derivados.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.database import db
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.oficio_iniciador_service import (
    get_or_create_iniciador_from_oficio,
)
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    assign_iniciador_domicilio_desde_origen,
    resolve_domicilio_operativo_para_iniciador,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    Expediente,
    IniciadorRuta,
    JuzgadoCatalogo,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_active_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"pr1_{_unique_num()}",
        email=f"pr1_{_unique_num()}@test.local",
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


def _mk_notificacion_vencida_con_actuacion(*, distrito_id: int | None = None) -> tuple[Actuaciones, Notificacion, Domicilio]:
    dom = Domicilio(calle=f"PR1Calle{_unique_num()}", numero="50", distrito_id=distrito_id)
    db.session.add(dom)
    db.session.flush()

    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()

    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=5)
    db.session.add(noti)
    db.session.flush()
    noti.fecha_notificacion = date(2026, 1, 10)
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    noti.plazo_dias = 5
    noti.prorroga_dias = 0
    db.session.add(noti)
    db.session.flush()

    act = Actuaciones(
        fecha=date(2026, 5, 1),
        mes=5,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        notificacion_id=noti.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti, dom


def _mk_oficio_circuito(domicilio_id: int) -> tuple[Actuaciones, Oficio, Expediente]:
    jz = JuzgadoCatalogo(codigo=f"JZPR1{_unique_num()}"[:32], nombre=f"Jz PR1 {_unique_num()}")
    db.session.add(jz)
    db.session.flush()

    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()

    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=5, motivo="pr1 oficio")
    db.session.add(comp)
    db.session.flush()

    act = Actuaciones(
        fecha=date(2026, 5, 2),
        mes=5,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
        domicilio_id=domicilio_id,
    )
    db.session.add(act)
    db.session.flush()

    ofi = Oficio(
        numero_oficio=_unique_num()[:8],
        anio=2026,
        fecha_oficio=date(2026, 5, 10),
        causa="PR1",
        juzgado_id=jz.id,
        comprobacion_id=comp.id,
    )
    db.session.add(ofi)
    db.session.flush()

    ex_resp = Expediente(
        numero_expediente=_unique_num()[:6],
        anio="2026",
        fecha_expediente=date(2026, 5, 12),
        tipo_expediente="RESPUESTA_OFICIO",
        comprobacion_id=comp.id,
        oficio_id=ofi.id,
    )
    db.session.add(ex_resp)
    db.session.flush()
    return act, ofi, ex_resp


def test_notificacion_hereda_domicilio_id_de_actuacion_origen(app_ctx) -> None:
    try:
        _ensure_active_user()
        act, noti, dom = _mk_notificacion_vencida_con_actuacion()
        dom_id = dom.id

        sync_iniciadores_reinspeccion_notificacion()

        ini = (
            IniciadorRuta.query.filter_by(
                notificacion_id=noti.id,
                tipo_iniciador="REINSPECCION_NOTIFICACION",
            )
            .order_by(IniciadorRuta.id.desc())
            .first()
        )
        assert ini is not None
        assert ini.domicilio_id == dom_id == act.domicilio_id
        assert Domicilio.query.filter(Domicilio.id == dom_id).count() == 1
    finally:
        db.session.rollback()


def test_domicilio_origen_con_distrito_iniciador_queda_con_mismo_domicilio(app_ctx) -> None:
    try:
        _ensure_active_user()
        dist = Distrito.query.order_by(Distrito.id.asc()).first()
        if not dist:
            pytest.skip("No hay distritos en BD para validar herencia de distrito")

        act, noti, dom = _mk_notificacion_vencida_con_actuacion(distrito_id=dist.id)
        sync_iniciadores_reinspeccion_notificacion()

        ini = IniciadorRuta.query.filter_by(notificacion_id=noti.id).first()
        assert ini is not None
        assert ini.domicilio_id == dom.id
        dom_ref = db.session.get(Domicilio, ini.domicilio_id)
        assert dom_ref is not None
        assert dom_ref.distrito_id == dist.id
    finally:
        db.session.rollback()


def test_geocode_ok_no_dispara_on_domicilio_changed_ni_duplica_geocode(app_ctx, monkeypatch) -> None:
    try:
        _ensure_active_user()
        act, _, dom = _mk_notificacion_vencida_con_actuacion()
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            lat=-26.8241,
            lng=-65.2226,
            geo_status="OK",
            addr_hash="pr1hash",
        )
        db.session.add(geo)
        db.session.flush()
        geo_count_before = DomicilioGeocode.query.filter_by(domicilio_id=dom.id).count()

        mock_on_changed = MagicMock()
        monkeypatch.setattr(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
            mock_on_changed,
        )

        resolved = resolve_domicilio_operativo_para_iniciador(dom.id)
        assert resolved == dom.id
        mock_on_changed.assert_not_called()
        assert (
            DomicilioGeocode.query.filter_by(domicilio_id=dom.id).count() == geo_count_before
        )
        assert act.domicilio_id == dom.id
    finally:
        db.session.rollback()


def test_backfill_distrito_si_geocode_ok_y_distrito_null(app_ctx, monkeypatch) -> None:
    try:
        _ensure_active_user()
        dist = Distrito.query.order_by(Distrito.id.asc()).first()
        if not dist:
            pytest.skip("No hay distritos en BD para validar backfill de distrito")

        dom = Domicilio(calle=f"BF{_unique_num()}", numero="10", distrito_id=None)
        db.session.add(dom)
        db.session.flush()
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
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

        resolve_domicilio_operativo_para_iniciador(dom.id)
        db.session.flush()
        dom_ref = db.session.get(Domicilio, dom.id)
        assert dom_ref is not None
        assert dom_ref.distrito_id == dist.id
    finally:
        db.session.rollback()


def test_oficio_hereda_domicilio_id_de_actuacion_origen(app_ctx) -> None:
    try:
        _ensure_active_user()
        dom = Domicilio(calle=f"OfPR1{_unique_num()}", numero="20")
        db.session.add(dom)
        db.session.flush()
        act, ofi, ex_resp = _mk_oficio_circuito(dom.id)

        ini = get_or_create_iniciador_from_oficio(
            actuacion=act,
            oficio=ofi,
            expediente_respuesta=ex_resp,
        )
        db.session.add(ini)
        db.session.flush()

        assert ini.domicilio_id == dom.id == act.domicilio_id
    finally:
        db.session.rollback()


def test_actuacion_sin_domicilio_oficio_no_crea_iniciador_con_domicilio_falso(app_ctx) -> None:
    try:
        _ensure_active_user()
        dom = Domicilio(calle=f"Tmp{_unique_num()}", numero="1")
        db.session.add(dom)
        db.session.flush()
        act, ofi, ex_resp = _mk_oficio_circuito(dom.id)
        act.domicilio_id = None
        db.session.add(act)
        db.session.flush()

        with pytest.raises(ValueError, match="no tiene domicilio"):
            get_or_create_iniciador_from_oficio(
                actuacion=act,
                oficio=ofi,
                expediente_respuesta=ex_resp,
            )
    finally:
        db.session.rollback()


def test_no_se_duplica_domicilio_al_crear_iniciador_derivado(app_ctx) -> None:
    try:
        _ensure_active_user()
        act, noti, dom = _mk_notificacion_vencida_con_actuacion()
        dom_id = act.domicilio_id

        sync_iniciadores_reinspeccion_notificacion()

        ini = IniciadorRuta.query.filter_by(notificacion_id=noti.id).first()
        assert ini is not None
        assert ini.domicilio_id == dom_id
        assert Domicilio.query.filter(Domicilio.id == dom_id).count() == 1
    finally:
        db.session.rollback()


def test_iniciador_cumplido_no_cambia_domicilio(app_ctx) -> None:
    try:
        _ensure_active_user()
        dom_origen = Domicilio(calle=f"Orig{_unique_num()}", numero="1")
        dom_viejo = Domicilio(calle=f"Viejo{_unique_num()}", numero="2")
        db.session.add_all([dom_origen, dom_viejo])
        db.session.flush()

        u = _ensure_active_user()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 5, 1),
            anio=2026,
            mes=5,
            domicilio_id=dom_viejo.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        assign_iniciador_domicilio_desde_origen(
            ini,
            dom_origen.id,
            allow_update_existing=True,
        )
        assert ini.domicilio_id == dom_viejo.id
    finally:
        db.session.rollback()


def test_iniciador_pendiente_actualiza_domicilio_snapshot_viejo(app_ctx) -> None:
    try:
        _ensure_active_user()
        dom_origen = Domicilio(calle=f"OrigP{_unique_num()}", numero="1")
        dom_viejo = Domicilio(calle=f"ViejoP{_unique_num()}", numero="2")
        db.session.add_all([dom_origen, dom_viejo])
        db.session.flush()

        act, ofi, ex_resp = _mk_oficio_circuito(dom_origen.id)
        u = _ensure_active_user()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date(2026, 5, 1),
            anio=2026,
            mes=5,
            domicilio_id=dom_viejo.id,
            prioridad=3,
            oficio_id=ofi.id,
            actuacion_id=act.id,
            comprobacion_id=act.comprobacion_id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        recovered = get_or_create_iniciador_from_oficio(
            actuacion=act,
            oficio=ofi,
            expediente_respuesta=ex_resp,
        )
        assert recovered.id == ini.id
        assert recovered.domicilio_id == dom_origen.id
    finally:
        db.session.rollback()


def test_denuncia_sigue_creando_iniciador_con_domicilio(app_ctx, monkeypatch) -> None:
    try:
        u = _ensure_active_user()
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )
        dom = Domicilio(calle=f"DenPR1{_unique_num()}", numero="99")
        db.session.add(dom)
        db.session.flush()

        den, ini = crear_denuncia_con_iniciador(
            fecha=date.today(),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="PR1 denuncia intacta",
        )
        db.session.flush()

        assert den.domicilio_id == dom.id
        assert ini.domicilio_id == dom.id
        assert ini.tipo_iniciador == "DENUNCIA"
        assert ini.estado_iniciador == "PENDIENTE"
    finally:
        db.session.rollback()
