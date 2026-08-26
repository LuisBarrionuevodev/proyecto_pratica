"""RUTA-ASIG.1 — detalle operativo en presenter de iniciadores y pool."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.rutas_trabajo.presenters.ruta_presenters import (
    iniciador_operativo_campos,
    iniciador_pendiente_to_row,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import ruta_pool_dia_row_dict
from app.models import (
    Comprobacion,
    Denuncia,
    Domicilio,
    DomicilioGeocode,
    Expediente,
    IniciadorRuta,
    Notificacion,
    Oficio,
    Relevamiento,
    Rubro,
    RutaPoolDia,
    User,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"asig1_{_unique_num()}",
        email=f"asig1_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def test_iniciador_notificacion_expone_numero_y_prorroga(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"Noti{_unique_num()}", numero="10")
        db.session.add(dom)
        db.session.flush()
        nnum = _unique_num()
        noti = Notificacion(
            numero_acta=nnum,
            anio=2026,
            mes=8,
            prorroga_dias=10,
            fecha_vencimiento=date(2026, 8, 24),
        )
        db.session.add(noti)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
            prioridad=3,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["tipo_iniciador_label"] == "Reinspección por notificación"
        assert row["identificadores"]["numero_notificacion"] == nnum
        assert row["identificadores"]["prorroga_dias"] == 10
        assert "Notif." in (row["detalle_operativo_texto"] or "")
        assert "Prórroga" in (row["detalle_operativo_texto"] or "")
    finally:
        db.session.rollback()


def test_iniciador_oficio_expone_comprobacion_expediente_oficio_causa(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"Ofi{_unique_num()}", numero="1")
        db.session.add(dom)
        db.session.flush()
        ncomp = _unique_num()
        comp = Comprobacion(numero_acta=ncomp, anio=2026, mes=8)
        db.session.add(comp)
        db.session.flush()
        nof = f"OF{_unique_num()[:5]}"
        ofi = Oficio(numero_oficio=nof, anio=2026, comprobacion_id=comp.id, causa="Ruidos molestos")
        db.session.add(ofi)
        db.session.flush()
        exp = Expediente(
            numero_expediente=_unique_num(),
            anio="2026",
            fecha_expediente=date(2026, 8, 1),
            oficio_id=ofi.id,
            tipo_expediente="RESPUESTA_OFICIO",
        )
        db.session.add(exp)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            oficio_id=ofi.id,
            comprobacion_id=comp.id,
            prioridad=2,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        campos = iniciador_operativo_campos(ini)
        texto = campos["detalle_operativo_texto"] or ""
        assert ncomp in texto
        assert nof in texto
        assert "Ruidos molestos" in texto
        assert campos["identificadores"]["numero_comprobacion"] == ncomp
    finally:
        db.session.rollback()


def test_iniciador_denuncia_expone_motivo(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"Den{_unique_num()}", numero="3")
        db.session.add(dom)
        db.session.flush()
        den = Denuncia(
            fecha=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            motivo="Alimentos en mal estado",
            created_by_user_id=u.id,
        )
        db.session.add(den)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            denuncia_id=den.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        row = iniciador_pendiente_to_row(ini)
        assert row["motivo_denuncia"] == "Alimentos en mal estado"
        assert "Alimentos en mal estado" in (row["detalle_operativo_texto"] or "")
    finally:
        db.session.rollback()


def test_iniciador_relevamiento_expone_rubro_y_fantasia(app_ctx) -> None:
    try:
        u = _mk_user()
        rub = Rubro(nombre=f"RubAsig1_{_unique_num()}")
        db.session.add(rub)
        db.session.flush()
        dom = Domicilio(calle=f"Rel{_unique_num()}", numero="5", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()
        rel = Relevamiento(
            fecha=date.today(),
            mes=8,
            anio=2026,
            inspector_id=1,
            domicilio_id=dom.id,
            rubro_id=rub.id,
            nombre_fantasia="El Toro",
            angulo_esquina="NE",
        )
        db.session.add(rel)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="RELEVAMIENTO",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            relevamiento_id=rel.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        campos = iniciador_operativo_campos(ini)
        texto = campos["detalle_operativo_texto"] or ""
        assert rub.nombre in texto
        assert "El Toro" in texto
    finally:
        db.session.rollback()


def test_pool_row_dict_incluye_tipo_iniciador_real(app_ctx) -> None:
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"Pool{_unique_num()}", numero="9")
        db.session.add(dom)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            prioridad=2,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        pool = RutaPoolDia(
            fecha=date.today(),
            estado="EN_POOL",
            origen_tipo="INICIADOR",
            iniciador_ruta_id=ini.id,
            domicilio_id=dom.id,
            usuario_id=u.id,
        )
        db.session.add(pool)
        db.session.flush()
        db.session.refresh(pool)

        row = ruta_pool_dia_row_dict(pool)
        assert row["tipo_iniciador"] == "DENUNCIA"
        assert row["tipo_iniciador_label"] == "Denuncia"
        assert row["prioridad"] == 2
    finally:
        db.session.rollback()


def test_pool_row_dict_incluye_geocode_desde_domicilio(app_ctx) -> None:
    """OPER-RUTA.FUNCIONAL-2A.1 — pool expone lat/lng/geo_status como M4 e ítems de ruta."""
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"PoolGeo{_unique_num()}", numero="42")
        db.session.add(dom)
        db.session.flush()
        geo = DomicilioGeocode(
            domicilio_id=dom.id,
            lat=-26.8245,
            lng=-65.2223,
            geo_status="OK",
        )
        db.session.add(geo)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            prioridad=2,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        pool = RutaPoolDia(
            fecha=date.today(),
            estado="EN_POOL",
            origen_tipo="INICIADOR",
            iniciador_ruta_id=ini.id,
            domicilio_id=dom.id,
            usuario_id=u.id,
        )
        db.session.add(pool)
        db.session.flush()
        db.session.refresh(pool)

        row = ruta_pool_dia_row_dict(pool)
        assert row["lat"] == pytest.approx(-26.8245)
        assert row["lng"] == pytest.approx(-65.2223)
        assert row["geo_status"] == "OK"
    finally:
        db.session.rollback()


def test_pool_row_dict_sin_geocode_expone_nulls(app_ctx) -> None:
    """OPER-RUTA.FUNCIONAL-2A.1 — domicilio sin geocode no inventa ubicación."""
    try:
        u = _mk_user()
        dom = Domicilio(calle=f"PoolSinGeo{_unique_num()}", numero="1")
        db.session.add(dom)
        db.session.flush()
        ini = IniciadorRuta(
            tipo_iniciador="DENUNCIA",
            estado_iniciador="PENDIENTE",
            fecha_origen=date.today(),
            anio=2026,
            mes=8,
            domicilio_id=dom.id,
            prioridad=1,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()
        pool = RutaPoolDia(
            fecha=date.today(),
            estado="EN_POOL",
            origen_tipo="INICIADOR",
            iniciador_ruta_id=ini.id,
            domicilio_id=dom.id,
            usuario_id=u.id,
        )
        db.session.add(pool)
        db.session.flush()
        db.session.refresh(pool)

        row = ruta_pool_dia_row_dict(pool)
        assert row["lat"] is None
        assert row["lng"] is None
        assert row["geo_status"] is None
    finally:
        db.session.rollback()
