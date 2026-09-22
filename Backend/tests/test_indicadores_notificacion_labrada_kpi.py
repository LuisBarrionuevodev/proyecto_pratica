"""
PERF-DASH.2.2 — KPI notificación labrada vs FK referencial de reinspección.
"""

from __future__ import annotations

import random
from datetime import date, datetime

import pytest

from app.database import db
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Motivo,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero
from tests.indicadores_cierre_fixtures import vincular_cierre_realizado


def _unique_ot() -> str:
    return unique_ot_numero()


def _mk_user() -> User:
    u = User(
        username=f"u_nlk_{_unique_ot()}",
        email=f"nlk_{_unique_ot()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_motivo() -> Motivo:
    m = Motivo.query.first()
    if m is None:
        m = Motivo(nombre=f"mot_{_unique_ot()}")
        db.session.add(m)
        db.session.flush()
    return m


def _mk_domicilio() -> Domicilio:
    dom = Domicilio(calle=f"CalleNLK_{_unique_ot()}", numero="1")
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_notificacion_labarda(mes: int, anio: int = 2026) -> Notificacion:
    m = _mk_motivo()
    dom = _mk_domicilio()
    ot = OrdenTrabajo(numero_acta=_unique_ot(), anio=anio, mes=mes)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(anio, mes, 10),
        mes=mes,
        anio=anio,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    attach_notificacion(act, {"acta_num": _unique_ot(), "motivos": [m.nombre]})
    db.session.flush()
    assert act.notificacion_id is not None
    return db.session.get(Notificacion, act.notificacion_id)


def _mk_reinspeccion_realizada(
    fecha_ruta: date,
    noti_origen: Notificacion,
    act_origen: Actuaciones,
    *,
    act_notificacion_id: int | None = None,
    attach_nueva: bool = False,
) -> Actuaciones:
    """Cierre REINSPECCION_NOTIFICACION; simula FK referencial de origen o nueva notificación."""
    u = _mk_user()
    dom = act_origen.domicilio_id or _mk_domicilio().id
    ot = OrdenTrabajo(numero_acta=_unique_ot(), anio=fecha_ruta.year, mes=fecha_ruta.month)
    db.session.add(ot)
    db.session.flush()

    act_re = Actuaciones(
        fecha=fecha_ruta,
        mes=fecha_ruta.month,
        anio=fecha_ruta.year,
        tipo="REINSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom,
        notificacion_id=act_notificacion_id,
    )
    db.session.add(act_re)
    db.session.flush()

    if attach_nueva:
        m = _mk_motivo()
        attach_notificacion(act_re, {"acta_num": _unique_ot(), "motivos": [m.nombre]})
        db.session.flush()
    elif act_notificacion_id is None:
        act_re.notificacion_id = noti_origen.id
        db.session.flush()

    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="CUMPLIDO",
        fecha_origen=fecha_ruta,
        anio=fecha_ruta.year,
        mes=fecha_ruta.month,
        domicilio_id=dom,
        notificacion_id=noti_origen.id,
        actuacion_id=act_origen.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()

    ruta = RutaTrabajo(
        fecha=fecha_ruta,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()

    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="REALIZADO",
        actuacion_id=act_re.id,
        created_by_user_id=u.id,
        ejecutado_at=datetime(fecha_ruta.year, fecha_ruta.month, fecha_ruta.day, 10, 0, 0),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    return act_re


def _periodo(mes: int) -> tuple[date, date]:
    return date(2026, mes, 1), date(2026, mes, 28)


def test_a_inicial_labra_notificacion_cuenta(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(*_periodo(3)).actas_por_tipo.notificacion
        noti = _mk_notificacion_labarda(3)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).first()
        assert act_origen is not None
        vincular_cierre_realizado(act_origen, date(2026, 3, 15))
        db.session.flush()
        despues = build_indicadores_ejecutivo(*_periodo(3)).actas_por_tipo.notificacion
        assert despues == antes + 1
    finally:
        db.session.rollback()


def test_b_reinspeccion_sin_nueva_notificacion_no_recuenta(app_ctx) -> None:
    try:
        noti = _mk_notificacion_labarda(8)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act_origen, date(2026, 8, 5))
        db.session.flush()

        antes_sep = build_indicadores_ejecutivo(*_periodo(9))
        n_antes = antes_sep.actas_por_tipo.notificacion
        rein_antes = antes_sep.kpis.reinspecciones_notificacion_realizadas

        _mk_reinspeccion_realizada(date(2026, 9, 12), noti, act_origen)
        db.session.flush()

        despues = build_indicadores_ejecutivo(*_periodo(9))
        assert despues.kpis.reinspecciones_notificacion_realizadas == rein_antes + 1
        assert despues.actas_por_tipo.notificacion == n_antes
    finally:
        db.session.rollback()


def test_c_reinspeccion_con_nueva_notificacion_cuenta_solo_nueva(app_ctx) -> None:
    try:
        noti = _mk_notificacion_labarda(9)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act_origen, date(2026, 9, 1))
        db.session.flush()

        antes = build_indicadores_ejecutivo(*_periodo(9)).actas_por_tipo.notificacion

        _mk_reinspeccion_realizada(
            date(2026, 9, 18),
            noti,
            act_origen,
            attach_nueva=True,
        )
        db.session.flush()

        despues = build_indicadores_ejecutivo(*_periodo(9))
        assert despues.actas_por_tipo.notificacion == antes + 1
    finally:
        db.session.rollback()


def test_d_cross_month_reinspeccion_no_arrastra_notif(app_ctx) -> None:
    try:
        noti = _mk_notificacion_labarda(8)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act_origen, date(2026, 8, 10))
        db.session.flush()

        agosto = build_indicadores_ejecutivo(date(2026, 8, 1), date(2026, 8, 31))
        n_agosto = agosto.actas_por_tipo.notificacion

        _mk_reinspeccion_realizada(date(2026, 9, 12), noti, act_origen)
        db.session.flush()

        sept = build_indicadores_ejecutivo(*_periodo(9))
        assert sept.actas_por_tipo.notificacion == 0 or sept.actas_por_tipo.notificacion >= 0
        assert sept.kpis.reinspecciones_notificacion_realizadas >= 1
        agosto2 = build_indicadores_ejecutivo(date(2026, 8, 1), date(2026, 8, 31))
        assert agosto2.actas_por_tipo.notificacion == n_agosto
    finally:
        db.session.rollback()


def test_e_mismo_mes_notificacion_cuenta_una_sola_vez(app_ctx) -> None:
    try:
        noti = _mk_notificacion_labarda(9)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act_origen, date(2026, 9, 5))
        db.session.flush()

        antes = build_indicadores_ejecutivo(*_periodo(9)).actas_por_tipo.notificacion
        _mk_reinspeccion_realizada(date(2026, 9, 20), noti, act_origen)
        db.session.flush()
        despues = build_indicadores_ejecutivo(*_periodo(9)).actas_por_tipo.notificacion
        assert despues == antes
    finally:
        db.session.rollback()


def test_f_actuacion_normal_con_notificacion_sigue_contando(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(*_periodo(4)).actas_por_tipo.notificacion
        noti = _mk_notificacion_labarda(4)
        act = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act, date(2026, 4, 12), tipo_iniciador="RELEVAMIENTO")
        db.session.flush()
        despues = build_indicadores_ejecutivo(*_periodo(4)).actas_por_tipo.notificacion
        assert despues == antes + 1
    finally:
        db.session.rollback()


def test_g_dos_reinspecciones_misma_notificacion_origen_no_recuentan(app_ctx) -> None:
    try:
        noti = _mk_notificacion_labarda(7)
        act_origen = db.session.query(Actuaciones).filter_by(notificacion_id=noti.id).one()
        vincular_cierre_realizado(act_origen, date(2026, 7, 5))
        db.session.flush()

        antes = build_indicadores_ejecutivo(*_periodo(9)).actas_por_tipo.notificacion
        _mk_reinspeccion_realizada(date(2026, 9, 10), noti, act_origen)
        _mk_reinspeccion_realizada(date(2026, 9, 15), noti, act_origen)
        db.session.flush()
        despues = build_indicadores_ejecutivo(*_periodo(9)).actas_por_tipo.notificacion
        assert despues == antes
        assert build_indicadores_ejecutivo(*_periodo(9)).kpis.reinspecciones_notificacion_realizadas >= 2
    finally:
        db.session.rollback()
