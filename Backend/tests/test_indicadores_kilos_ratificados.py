"""V1.1-INDICADORES-RATIFICACION.1 — kilos ratificados por fecha de ruta."""

from __future__ import annotations

import random
from datetime import date

import pytest
from geoalchemy2 import WKTElement

from app.database import db
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from tests.indicadores_cierre_fixtures import (
    vincular_cierre_no_realizado,
    vincular_cierre_realizado,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    Inspector,
    OrdenTrabajo,
    Rubro,
    Turno,
)
from app.models.turno import TipoTurno
from tests.helpers.fixture_isolation import unique_ot_numero

_NOV_DESDE = date(2098, 11, 1)
_NOV_HASTA = date(2098, 11, 30)
_NOV = date(2098, 11, 12)
_AGO_DESDE = date(2098, 8, 1)
_AGO_HASTA = date(2098, 8, 31)
_AGO = date(2098, 8, 10)
_DIC_DESDE = date(2098, 12, 1)
_DIC_HASTA = date(2098, 12, 31)
_DIC = date(2098, 12, 5)


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{unique_ot_numero()}"


def _mk_actuacion(
    fecha: date,
    *,
    domicilio_id: int | None = None,
    tipo: str = "COMPROBACION",
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo=tipo,
        orden_trabajo_id=ot.id,
        domicilio_id=domicilio_id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_domicilio(*, distrito_id: int | None = None) -> Domicilio:
    rub = Rubro(nombre=_unique_name("RubKr"))
    db.session.add(rub)
    db.session.flush()
    c = Contribuyente(
        apellido="Kr",
        nombre="T",
        documento=str(random.randint(10_000_000, 99_999_999)),
    )
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CKr"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_inspector() -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(nombre=_unique_name("InspKr"), legajo=unique_ot_numero()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _ancla_con_decomiso(fecha: date, dom: Domicilio, kilos: float) -> Actuaciones:
    ancla = _mk_actuacion(fecha, domicilio_id=dom.id, tipo="COMPROBACION")
    attach_decomiso(ancla, {"acta_num": unique_ot_numero(), "kilos_total": kilos})
    db.session.flush()
    return ancla


def _visita_ratificacion(
    fecha: date,
    dom: Domicilio,
    ancla: Actuaciones,
    *,
    tipo: str = "RATIFICACION DE DECOMISO",
    tipo_iniciador: str = "RATIFICACION_DECOMISO_OFICIO",
    inspector_id: int | None = None,
) -> Actuaciones:
    visita = _mk_actuacion(fecha, domicilio_id=dom.id, tipo=tipo)
    vincular_cierre_realizado(
        visita,
        fecha,
        tipo_iniciador=tipo_iniciador,
        iniciador_actuacion_id=ancla.id,
        inspector_id=inspector_id,
    )
    db.session.flush()
    return visita


@pytest.mark.parametrize(
    "tipo,tipo_iniciador",
    [
        ("RATIFICACION DE DECOMISO", "RATIFICACION_DECOMISO_OFICIO"),
        ("RATIFICACION DE DECOMISO", "REINSPECCION_OFICIO"),
    ],
)
def test_decomiso_origen_ratificado_en_periodo_suma_kilos(app_ctx, tipo, tipo_iniciador) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 13.4)
        _visita_ratificacion(_NOV, dom, ancla, tipo=tipo, tipo_iniciador=tipo_iniciador)
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados + 13.4)
        assert out.kpis.mercaderia_decomisada_kg == pytest.approx(antes.kpis.mercaderia_decomisada_kg)
    finally:
        db.session.rollback()


def test_decomiso_en_agosto_ratificado_en_noviembre_cuenta_noviembre(app_ctx) -> None:
    try:
        ago_antes = build_indicadores_ejecutivo(_AGO_DESDE, _AGO_HASTA)
        nov_antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 13.4)
        _visita_ratificacion(_NOV, dom, ancla)
        ago = build_indicadores_ejecutivo(_AGO_DESDE, _AGO_HASTA)
        nov = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert ago.kpis.kilos_ratificados == pytest.approx(ago_antes.kpis.kilos_ratificados)
        assert nov.kpis.kilos_ratificados == pytest.approx(nov_antes.kpis.kilos_ratificados + 13.4)
    finally:
        db.session.rollback()


def test_ratificacion_clausura_con_decomiso_origen_no_suma(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 20.0)
        _visita_ratificacion(
            _NOV,
            dom,
            ancla,
            tipo="RATIFICACION DE CLAUSURA",
            tipo_iniciador="RATIFICACION_CLAUSURA_OFICIO",
        )
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_verificar_informar_con_decomiso_origen_no_suma(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 18.5)
        _visita_ratificacion(
            _NOV,
            dom,
            ancla,
            tipo="VERIFICAR E INFORMAR",
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        )
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_verificar_informar_con_decomiso_propio_no_suma(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _mk_actuacion(_AGO, domicilio_id=dom.id, tipo="COMPROBACION")
        visita = _visita_ratificacion(
            _NOV,
            dom,
            ancla,
            tipo="VERIFICAR E INFORMAR",
            tipo_iniciador="VERIFICAR_INFORMAR_OFICIO",
        )
        attach_decomiso(visita, {"acta_num": unique_ot_numero(), "kilos_total": 99.9})
        db.session.flush()
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_ratificacion_decomiso_sin_decomiso_en_ancla_suma_cero(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _mk_actuacion(_AGO, domicilio_id=dom.id, tipo="COMPROBACION")
        _visita_ratificacion(_NOV, dom, ancla)
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_dos_visitas_mismo_decomiso_cuentan_solo_primera_ratificacion(app_ctx) -> None:
    try:
        nov_antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dic_antes = build_indicadores_ejecutivo(_DIC_DESDE, _DIC_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 13.4)
        _visita_ratificacion(_NOV, dom, ancla)
        _visita_ratificacion(_DIC, dom, ancla)
        nov = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dic = build_indicadores_ejecutivo(_DIC_DESDE, _DIC_HASTA)
        assert nov.kpis.kilos_ratificados == pytest.approx(nov_antes.kpis.kilos_ratificados + 13.4)
        assert dic.kpis.kilos_ratificados == pytest.approx(dic_antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_visita_no_realizada_no_suma_kilos_ratificados(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 13.4)
        visita = _mk_actuacion(_NOV, domicilio_id=dom.id, tipo="RATIFICACION DE DECOMISO")
        item = vincular_cierre_no_realizado(
            visita,
            _NOV,
            tipo_iniciador="RATIFICACION_DECOMISO_OFICIO",
        )
        item.iniciador_ruta.actuacion_id = ancla.id
        db.session.flush()
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def _mk_distrito() -> Distrito:
    d = Distrito(
        nombre=_unique_name("DistKr"),
        codigo=random.randint(50_000, 99_999),
        geom=WKTElement("POLYGON((0 0, 0.01 0, 0.01 0.01, 0 0.01, 0 0))", srid=4326),
    )
    db.session.add(d)
    db.session.flush()
    return d


def test_kilos_ratificados_respeta_filtro_distrito(app_ctx) -> None:
    try:
        d_a = _mk_distrito()
        d_b = _mk_distrito()
        antes_a = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, distrito_id=d_a.id)
        antes_b = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, distrito_id=d_b.id)
        dom_a = _mk_domicilio(distrito_id=d_a.id)
        ancla = _ancla_con_decomiso(_AGO, dom_a, 7.25)
        _visita_ratificacion(_NOV, dom_a, ancla)
        out_a = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, distrito_id=d_a.id)
        out_b = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, distrito_id=d_b.id)
        assert out_a.kpis.kilos_ratificados == pytest.approx(antes_a.kpis.kilos_ratificados + 7.25)
        assert out_b.kpis.kilos_ratificados == pytest.approx(antes_b.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_kilos_ratificados_respeta_filtro_inspector(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        otro = _mk_inspector()
        antes_ins = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, inspector_id=ins.id)
        antes_otro = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, inspector_id=otro.id)
        dom = _mk_domicilio()
        ancla = _ancla_con_decomiso(_AGO, dom, 4.0)
        _visita_ratificacion(_NOV, dom, ancla, inspector_id=ins.id)
        out_ins = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, inspector_id=ins.id)
        out_otro = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA, inspector_id=otro.id)
        assert out_ins.kpis.kilos_ratificados == pytest.approx(antes_ins.kpis.kilos_ratificados + 4.0)
        assert out_otro.kpis.kilos_ratificados == pytest.approx(antes_otro.kpis.kilos_ratificados)
    finally:
        db.session.rollback()


def test_decomiso_cargado_en_visita_de_ratificacion_no_suma(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        dom = _mk_domicilio()
        ancla = _mk_actuacion(_AGO, domicilio_id=dom.id, tipo="COMPROBACION")
        visita = _visita_ratificacion(_NOV, dom, ancla)
        attach_decomiso(visita, {"acta_num": unique_ot_numero(), "kilos_total": 50.0})
        db.session.flush()
        out = build_indicadores_ejecutivo(_NOV_DESDE, _NOV_HASTA)
        assert out.kpis.kilos_ratificados == pytest.approx(antes.kpis.kilos_ratificados)
    finally:
        db.session.rollback()
