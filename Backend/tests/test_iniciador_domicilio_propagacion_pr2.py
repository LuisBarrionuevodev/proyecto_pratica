"""
PR2 — Propagación CRUD de domicilio a iniciadores activos.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    propagar_domicilio_a_iniciadores_activos,
    resolve_domicilio_operativo_para_iniciador,
)
from app.models import (
    Actuaciones,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Inspector,
    Notificacion,
    OrdenTrabajo,
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


def _ensure_active_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username=f"pr2_{_unique_num()}",
        email=f"pr2_{_unique_num()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _inspector_y_rubro() -> tuple[Inspector, Rubro]:
    ins = Inspector.query.first()
    rub = Rubro.query.first()
    if ins is None or rub is None:
        pytest.skip("Se requiere inspector y rubro en BD")
    return ins, rub


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _payload_relevamiento(*, calle: str, numero: str, ins: Inspector, rub: Rubro, fecha: str = "2026-06-10"):
    return {
        "fecha": fecha,
        "inspector_nombre": ins.nombre,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rub.nombre,
    }


def test_editar_relevamiento_pendiente_actualiza_iniciador(app_ctx) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        calle = _uniq("PR2Rel")
        rel = crear_relevamiento_desde_payload(_payload_relevamiento(calle=calle, numero="10", ins=ins, rub=rub))
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, tipo_iniciador="RELEVAMIENTO").first()
        assert ini is not None
        dom_antes = ini.domicilio_id

        nueva_calle = _uniq("PR2RelNueva")
        actualizar_relevamiento(
            rel.id,
            _payload_relevamiento(calle=nueva_calle, numero="20", ins=ins, rub=rub, fecha="2026-06-11"),
        )

        db.session.refresh(rel)
        db.session.refresh(ini)
        assert rel.domicilio_id == dom_antes
        assert ini.domicilio_id == rel.domicilio_id
        dom_db = db.session.get(Domicilio, dom_antes)
        assert dom_db is not None
        assert dom_db.calle == nueva_calle
        assert dom_db.numero == "20"
    finally:
        db.session.rollback()


def test_editar_relevamiento_iniciador_cumplido_no_actualiza(app_ctx) -> None:
    try:
        _ensure_active_user()
        u = _ensure_active_user()
        dom_origen = Domicilio(calle=_uniq("OrigC"), numero="1")
        dom_viejo = Domicilio(calle=_uniq("ViejoC"), numero="2")
        db.session.add_all([dom_origen, dom_viejo])
        db.session.flush()

        rel = Relevamiento(
            fecha=date(2026, 6, 1),
            mes=6,
            anio=2026,
            inspector_id=Inspector.query.first().id,
            domicilio_id=dom_origen.id,
            rubro_id=Rubro.query.first().id,
        )
        db.session.add(rel)
        db.session.flush()

        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="CUMPLIDO",
            fecha_origen=date(2026, 6, 1),
            anio=2026,
            mes=6,
            domicilio_id=dom_viejo.id,
            prioridad=1,
            relevamiento_id=rel.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        outcome = propagar_domicilio_a_iniciadores_activos("RELEVAMIENTO", rel.id, dom_origen.id)
        db.session.flush()

        assert outcome.actualizados == 0
        assert outcome.omitidos_estado_terminal == 1
        assert ini.domicilio_id == dom_viejo.id
    finally:
        db.session.rollback()


def test_propagacion_no_dispara_geocode_si_nuevo_domicilio_ya_ok(app_ctx, monkeypatch) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        calle = _uniq("PR2Geo")
        rel = crear_relevamiento_desde_payload(_payload_relevamiento(calle=calle, numero="30", ins=ins, rub=rub))
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id).first()
        assert ini is not None

        dom_nuevo = Domicilio(calle=_uniq("GeoOK"), numero="40")
        db.session.add(dom_nuevo)
        db.session.flush()
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom_nuevo.id,
                lat=-26.8241,
                lng=-65.2226,
                geo_status="OK",
                addr_hash="pr2ok",
            )
        )
        db.session.flush()
        geo_count = DomicilioGeocode.query.filter_by(domicilio_id=dom_nuevo.id).count()

        mock_on = MagicMock()
        monkeypatch.setattr(
            "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed",
            mock_on,
        )

        resolve_domicilio_operativo_para_iniciador(dom_nuevo.id)
        propagar_domicilio_a_iniciadores_activos("RELEVAMIENTO", rel.id, dom_nuevo.id)
        mock_on.assert_not_called()
        assert DomicilioGeocode.query.filter_by(domicilio_id=dom_nuevo.id).count() == geo_count
    finally:
        db.session.rollback()


def test_backfill_distrito_en_propagacion(app_ctx, monkeypatch) -> None:
    try:
        _ensure_active_user()
        dist = Distrito.query.order_by(Distrito.id.asc()).first()
        if not dist:
            pytest.skip("Sin distritos en BD")

        ins, rub = _inspector_y_rubro()
        rel = crear_relevamiento_desde_payload(
            _payload_relevamiento(calle=_uniq("PR2Dist"), numero="50", ins=ins, rub=rub)
        )

        dom = Domicilio(calle=_uniq("BFpr2"), numero="60", distrito_id=None)
        db.session.add(dom)
        db.session.flush()
        db.session.add(
            DomicilioGeocode(domicilio_id=dom.id, lat=-26.8241, lng=-65.2226, geo_status="OK")
        )
        db.session.flush()

        monkeypatch.setattr(
            "app.domains.geolocalizacion.geocode.services.distrito_backfill_service.resolve_distrito_id",
            lambda _lat, _lng: dist.id,
        )

        propagar_domicilio_a_iniciadores_activos("RELEVAMIENTO", rel.id, dom.id)
        db.session.flush()
        dom_ref = db.session.get(Domicilio, dom.id)
        assert dom_ref is not None
        assert dom_ref.distrito_id == dist.id
    finally:
        db.session.rollback()


def test_domicilio_anterior_no_se_borra_si_sigue_referenciado(app_ctx) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        calle = _uniq("PR2Ref")
        rel = crear_relevamiento_desde_payload(_payload_relevamiento(calle=calle, numero="70", ins=ins, rub=rub))
        old_dom_id = rel.domicilio_id

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()
        act_ref = Actuaciones(
            fecha=date(2026, 6, 5),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=old_dom_id,
        )
        db.session.add(act_ref)
        db.session.flush()

        actualizar_relevamiento(
            rel.id,
            _payload_relevamiento(calle=_uniq("PR2RefNuevo"), numero="80", ins=ins, rub=rub, fecha="2026-06-12"),
        )

        old_dom = db.session.get(Domicilio, old_dom_id)
        assert old_dom is not None
        assert old_dom.deleted_at is None
    finally:
        db.session.rollback()


def test_actuacion_propaga_domicilio_a_iniciador_activo(app_ctx) -> None:
    try:
        _ensure_active_user()
        u = _ensure_active_user()

        dom_old = Domicilio(calle=_uniq("ActOld"), numero="1")
        dom_new = Domicilio(calle=_uniq("ActNew"), numero="2")
        db.session.add_all([dom_old, dom_new])
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()

        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(noti)
        db.session.flush()
        noti.fecha_vencimiento = date.today() - timedelta(days=1)
        db.session.add(noti)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 6, 3),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom_old.id,
            notificacion_id=noti.id,
        )
        db.session.add(act)
        db.session.flush()

        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=6,
            domicilio_id=dom_old.id,
            prioridad=3,
            notificacion_id=noti.id,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        act.domicilio_id = dom_new.id
        db.session.add(act)
        db.session.commit()

        outcome = propagar_domicilio_a_iniciadores_activos("ACTUACION", act.id, dom_new.id)
        db.session.commit()

        assert outcome.actualizados == 1
        db.session.refresh(ini)
        assert ini.domicilio_id == dom_new.id
    finally:
        db.session.rollback()


def test_denuncia_sigue_funcionando(app_ctx, monkeypatch) -> None:
    try:
        u = _ensure_active_user()
        monkeypatch.setattr(
            "app.domains.denuncias.services.denuncias_service._get_current_user_id",
            lambda: int(u.id),
        )
        dom = Domicilio(calle=_uniq("DenPR2"), numero="99")
        db.session.add(dom)
        db.session.flush()

        den, ini = crear_denuncia_con_iniciador(
            fecha=date.today(),
            domicilio_id=dom.id,
            calle=None,
            numero=None,
            interseccion=None,
            motivo="PR2 denuncia ok",
        )
        assert den.domicilio_id == dom.id
        assert ini.domicilio_id == dom.id
    finally:
        db.session.rollback()


def test_ruta_publicada_no_muta_iniciador(app_ctx) -> None:
    try:
        _ensure_active_user()
        u = _ensure_active_user()

        dom_old = Domicilio(calle=_uniq("PubOld"), numero="1")
        dom_new = Domicilio(calle=_uniq("PubNew"), numero="2")
        db.session.add_all([dom_old, dom_new])
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 6, 8),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom_old.id,
        )
        db.session.add(act)
        db.session.flush()

        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PLANIFICADO",
            fecha_origen=date(2026, 6, 8),
            anio=2026,
            mes=6,
            domicilio_id=dom_old.id,
            prioridad=3,
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ruta = RutaTrabajo(
            fecha=date(2026, 6, 9),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
            numero=random.randint(2, 32000),
        )
        db.session.add(ruta)
        db.session.flush()
        db.session.add(
            RutaItem(
                ruta_trabajo_id=ruta.id,
                iniciador_ruta_id=ini.id,
                orden_trabajo_id=ot.id,
                estado_ruta_item="ASIGNADO",
                actuacion_id=act.id,
                created_by_user_id=u.id,
            )
        )
        db.session.flush()

        outcome = propagar_domicilio_a_iniciadores_activos("ACTUACION", act.id, dom_new.id)
        assert outcome.actualizados == 0
        assert outcome.omitidos_ruta_publicada == 1
        assert ini.domicilio_id == dom_old.id
    finally:
        db.session.rollback()


def test_no_duplica_domicilio_en_propagacion(app_ctx) -> None:
    try:
        ins, rub = _inspector_y_rubro()
        rel = crear_relevamiento_desde_payload(
            _payload_relevamiento(calle=_uniq("PR2Dup"), numero="90", ins=ins, rub=rub)
        )
        dom_id = rel.domicilio_id
        propagar_domicilio_a_iniciadores_activos("RELEVAMIENTO", rel.id, rel.domicilio_id)
        ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id).first()
        assert ini is not None
        assert ini.domicilio_id == dom_id
        assert Domicilio.query.filter(Domicilio.id == dom_id).count() == 1
    finally:
        db.session.rollback()


def test_pr1_creacion_iniciador_sigue_heredando(app_ctx) -> None:
    try:
        _ensure_active_user()
        dom = Domicilio(calle=_uniq("PR1sig"), numero="11")
        db.session.add(dom)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(ot)
        db.session.flush()

        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
        db.session.add(noti)
        db.session.flush()
        noti.fecha_vencimiento = date.today() - timedelta(days=2)
        db.session.add(noti)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 6, 1),
            mes=6,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
        )
        db.session.add(act)
        db.session.flush()

        sync_iniciadores_reinspeccion_notificacion()
        ini = IniciadorRuta.query.filter_by(notificacion_id=noti.id).first()
        assert ini is not None
        assert ini.domicilio_id == dom.id
    finally:
        db.session.rollback()
