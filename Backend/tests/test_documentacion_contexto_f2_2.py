"""F2.2: contexto documental en `actuacion_to_grid_row` (circuito, propia, origen reinspección)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app import create_app
from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    build_actuacion_grid_batch_maps,
    build_iniciador_ruta_por_actuacion_id,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Domicilio,
    Expediente,
    IniciadorRuta,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_comun_notificacion_usa_expediente_de_notificacion(app_ctx) -> None:
    try:
        ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()
        noti = Notificacion(numero_acta=_ot_num(), anio=2026, mes=3, plazo_dias=5, prorroga_dias=0)
        db.session.add(noti)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="001010",
                anio="2026",
                tipo_expediente="ENVIO_ACTA",
                notificacion_id=noti.id,
                comprobacion_id=None,
                oficio_id=None,
            )
        )
        act = Actuaciones(
            fecha=date(2026, 3, 15),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            notificacion_id=noti.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()
        row = actuacion_to_grid_row(act)
        assert row["documentacion_contexto"]["circuito"] == "COMUN_NOTIFICACION"
        assert row["expediente_numero"] == "001010"
        assert row["expediente_anio"] == "2026"
        assert row["oficio_numero"] is None
        assert row["origen_reinspeccion_oficio"] is None
        assert row["origen_reinspeccion_notificacion"] is None
    finally:
        db.session.rollback()


def test_reinspeccion_oficio_expone_origen_vía_ruta_item(app_ctx) -> None:
    try:
        u = User(
            username=f"u_f22_{random.randint(0, 999999)}",
            email=f"f22_{random.randint(0, 999999)}@t.local",
            password_hash="x",
            role="usuario",
            is_active=True,
        )
        db.session.add(u)
        db.session.flush()
        dom = Domicilio(calle=f"F22_{random.randint(0, 99999)}", numero="1")
        db.session.add(dom)
        db.session.flush()

        comp_origen = Comprobacion(numero_acta=_ot_num(), anio=2026, mes=3, motivo="origen")
        db.session.add(comp_origen)
        db.session.flush()
        ofi = Oficio(numero_oficio="12", anio=2026, comprobacion_id=comp_origen.id, causa="Falta higiene")
        db.session.add(ofi)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="007777",
                anio="2026",
                tipo_expediente="RESPUESTA_OFICIO",
                comprobacion_id=comp_origen.id,
                oficio_id=ofi.id,
            )
        )
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_OFICIO",
            estado_iniciador="EN_EJECUCION",
            fecha_origen=date(2026, 4, 1),
            anio=2026,
            mes=4,
            domicilio_id=dom.id,
            comprobacion_id=comp_origen.id,
            oficio_id=ofi.id,
            created_by_user_id=u.id,
        )
        db.session.add(ini)
        db.session.flush()

        ruta = RutaTrabajo(
            fecha=date(2026, 4, 10),
            turno="MANIANA",
            estado_ruta="PUBLICADA",
            created_by_user_id=u.id,
        )
        db.session.add(ruta)
        db.session.flush()

        ot_visita = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=4)
        db.session.add(ot_visita)
        db.session.flush()
        comp_visita = Comprobacion(numero_acta=_ot_num(), anio=2026, mes=4, motivo="visita")
        db.session.add(comp_visita)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 4, 10),
            mes=4,
            anio=2026,
            tipo="REINSPECCION",
            orden_trabajo_id=ot_visita.id,
            comprobacion_id=comp_visita.id,
        )
        db.session.add(act)
        db.session.flush()
        db.session.add(
            Expediente(
                numero_expediente="002222",
                anio="2026",
                tipo_expediente="ENVIO_ACTA",
                comprobacion_id=comp_visita.id,
                oficio_id=None,
            )
        )

        item = RutaItem(
            ruta_trabajo_id=ruta.id,
            iniciador_ruta_id=ini.id,
            orden_trabajo_id=ot_visita.id,
            estado_ruta_item="EN_PROCESO",
            actuacion_id=act.id,
            created_by_user_id=u.id,
        )
        db.session.add(item)
        db.session.flush()

        m = build_iniciador_ruta_por_actuacion_id([act.id])
        assert m.get(act.id) is not None
        batch = build_actuacion_grid_batch_maps([act], m)
        row = actuacion_to_grid_row(
            act,
            iniciador_desde_ruta=m.get(act.id),
            batch=batch,
        )
        assert row["documentacion_contexto"]["circuito"] == "REINSPECCION_OFICIO"
        assert row["oficio_numero"] is None
        assert row["origen_reinspeccion_oficio"] is not None
        assert row["origen_reinspeccion_oficio"]["comprobacion_acta_numero"] == comp_origen.numero_acta
        assert row["origen_reinspeccion_oficio"]["oficio_numero"] == "12"
        assert row["origen_reinspeccion_oficio"]["oficio_causa"] == "Falta higiene"
        assert row["origen_reinspeccion_oficio"]["expediente_numero"] == "007777"
    finally:
        db.session.rollback()
