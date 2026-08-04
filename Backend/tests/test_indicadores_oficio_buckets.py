"""
Tests bucket híbrido oficio + actuaciones.tipo (D1d.11fix-a3).
"""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    bucket_operativo,
    visitas_realizadas_por_tipo_iniciador,
)
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from tests.indicadores_cierre_fixtures import vincular_cierre_realizado
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    Inspector,
    OrdenTrabajo,
    Rubro,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_DESDE = date(2099, 7, 1)
_HASTA = date(2099, 7, 31)
_FECHA = date(2099, 7, 15)


def _unique_ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{_unique_ot_num()}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion(
    fecha: date,
    *,
    domicilio_id: int | None = None,
    tipo: str = "INSPECCION",
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=fecha.year, mes=fecha.month)
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


def _mk_domicilio_con_rubro(nombre_rubro: str | None = None, distrito_id: int | None = None) -> Domicilio:
    rub = Rubro(nombre=nombre_rubro or _unique_name("RubOf"))
    db.session.add(rub)
    db.session.flush()
    c = Contribuyente(apellido="Of", nombre="T", documento=str(random.randint(10_000_000, 99_999_999)))
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("COf"),
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
    ins = Inspector(nombre=_unique_name("InspOf"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _cierre_oficio_hibrido(act_tipo: str) -> None:
    dom = _mk_domicilio_con_rubro()
    act = _mk_actuacion(_FECHA, domicilio_id=dom.id, tipo=act_tipo)
    vincular_cierre_realizado(act, _FECHA, tipo_iniciador="REINSPECCION_OFICIO")


@pytest.mark.parametrize(
    "act_tipo,kpi_field",
    [
        ("RATIFICACION DE CLAUSURA", "ratificaciones_clausura_realizadas"),
        ("RATIFICACION DE DECOMISO", "ratificaciones_decomiso_realizadas"),
        ("VERIFICAR E INFORMAR", "verificar_informar_realizadas"),
    ],
)
def test_reinspeccion_oficio_subtipo_cuenta_kpi(app_ctx, act_tipo, kpi_field) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        _cierre_oficio_hibrido(act_tipo)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert getattr(out.kpis, kpi_field) == getattr(antes.kpis, kpi_field) + 1
    finally:
        db.session.rollback()


def test_reinspeccion_oficio_generica_no_suma_ratificaciones(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        _cierre_oficio_hibrido("REINSPECCION")
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.ratificaciones_clausura_realizadas == antes.kpis.ratificaciones_clausura_realizadas
        assert out.kpis.ratificaciones_decomiso_realizadas == antes.kpis.ratificaciones_decomiso_realizadas
        assert out.kpis.verificar_informar_realizadas == antes.kpis.verificar_informar_realizadas
        por_tipo = visitas_realizadas_por_tipo_iniciador(_DESDE, _HASTA)
        assert por_tipo.get("REINSPECCION_OFICIO", 0) >= 1
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "tipo_iniciador,kpi_field",
    [
        ("RATIFICACION_CLAUSURA_OFICIO", "ratificaciones_clausura_realizadas"),
        ("RATIFICACION_DECOMISO_OFICIO", "ratificaciones_decomiso_realizadas"),
        ("VERIFICAR_INFORMAR_OFICIO", "verificar_informar_realizadas"),
    ],
)
def test_enum_directo_iniciador_sigue_contando(app_ctx, tipo_iniciador, kpi_field) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion(_FECHA, domicilio_id=dom.id, tipo="REINSPECCION")
        vincular_cierre_realizado(act, _FECHA, tipo_iniciador=tipo_iniciador)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert getattr(out.kpis, kpi_field) == getattr(antes.kpis, kpi_field) + 1
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "act_tipo,expected_bucket",
    [
        ("RATIFICACION DE CLAUSURA", "RATIFICACION_CLAUSURA"),
        ("RATIFICACIÓN DE CLAUSURA", "RATIFICACION_CLAUSURA"),
        ("ratificacion_clausura", "RATIFICACION_CLAUSURA"),
        ("ratificacionClausura", "RATIFICACION_CLAUSURA"),
        ("RATIFICACION DE DECOMISO", "RATIFICACION_DECOMISO"),
        ("ratificacion de decomiso", "RATIFICACION_DECOMISO"),
        ("VERIFICAR E INFORMAR", "VERIFICAR_INFORMAR"),
        ("verificar e informar", "VERIFICAR_INFORMAR"),
    ],
)
def test_bucket_normaliza_variantes_actuacion_tipo(act_tipo, expected_bucket) -> None:
    assert bucket_operativo("REINSPECCION_OFICIO", act_tipo) == expected_bucket


def test_top_rubros_con_domicilio_actuacion(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubActDom")
        dom = _mk_domicilio_con_rubro(rub_nombre)
        act = _mk_actuacion(_FECHA, domicilio_id=dom.id)
        vincular_cierre_realizado(act, _FECHA)
        db.session.flush()
        out = build_indicadores_riesgo(_DESDE, _HASTA)
        rubros = {r.rubro: r.cantidad for r in out.top_rubros}
        assert rubros.get(rub_nombre, 0) == 1
    finally:
        db.session.rollback()


def test_top_rubros_fallback_domicilio_iniciador(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubIniDom")
        dom_ini = _mk_domicilio_con_rubro(rub_nombre)
        act = _mk_actuacion(_FECHA, domicilio_id=None, tipo="RATIFICACION DE CLAUSURA")
        vincular_cierre_realizado(
            act,
            _FECHA,
            tipo_iniciador="REINSPECCION_OFICIO",
            ini_domicilio_id=dom_ini.id,
        )
        db.session.flush()
        out = build_indicadores_riesgo(_DESDE, _HASTA)
        rubros = {r.rubro: r.cantidad for r in out.top_rubros}
        assert rubros.get(rub_nombre, 0) == 1
    finally:
        db.session.rollback()


def test_filtro_distrito_bucket_hibrido(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos.")
        d_a, d_b = distritos[0], distritos[1]
        if d_a.id == d_b.id:
            pytest.skip("Se requieren 2 distritos distintos.")

        dom_a = _mk_domicilio_con_rubro(nombre_rubro=_unique_name("RubDA"), distrito_id=d_a.id)
        dom_b = _mk_domicilio_con_rubro(nombre_rubro=_unique_name("RubDB"), distrito_id=d_b.id)
        act_a = _mk_actuacion(_FECHA, domicilio_id=dom_a.id, tipo="RATIFICACION DE CLAUSURA")
        act_b = _mk_actuacion(_FECHA, domicilio_id=dom_b.id, tipo="RATIFICACION DE DECOMISO")
        vincular_cierre_realizado(act_a, _FECHA, tipo_iniciador="REINSPECCION_OFICIO")
        vincular_cierre_realizado(act_b, _FECHA, tipo_iniciador="REINSPECCION_OFICIO")
        db.session.flush()

        out_a = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_a.id)
        out_b = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_b.id)
        assert out_a.kpis.ratificaciones_clausura_realizadas >= 1
        assert out_b.kpis.ratificaciones_decomiso_realizadas >= 1
    finally:
        db.session.rollback()


def test_filtro_inspector_bucket_hibrido_sin_duplicar(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion(_FECHA, domicilio_id=dom.id, tipo="RATIFICACION DE CLAUSURA")
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins.id,
            )
        )
        vincular_cierre_realizado(
            act, _FECHA, tipo_iniciador="REINSPECCION_OFICIO", inspector_id=ins.id
        )
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins.id)
        assert out.kpis.ratificaciones_clausura_realizadas == 1
        assert out.kpis.reinspecciones_oficio_realizadas == 1
    finally:
        db.session.rollback()


def test_ejecutivo_incluye_reinspecciones_oficio_realizadas_cero(app_ctx) -> None:
    try:
        out = build_indicadores_ejecutivo(date(2090, 1, 1), date(2090, 1, 31))
        assert out.kpis.reinspecciones_oficio_realizadas == 0
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "act_tipo,kpi_field",
    [
        ("RATIFICACION DE CLAUSURA", "ratificaciones_clausura_realizadas"),
        ("RATIFICACION DE DECOMISO", "ratificaciones_decomiso_realizadas"),
        ("VERIFICAR E INFORMAR", "verificar_informar_realizadas"),
    ],
)
def test_reinspeccion_oficio_subtipo_suma_universo_oficio(app_ctx, act_tipo, kpi_field) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        _cierre_oficio_hibrido(act_tipo)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.reinspecciones_oficio_realizadas == antes.kpis.reinspecciones_oficio_realizadas + 1
        assert getattr(out.kpis, kpi_field) == getattr(antes.kpis, kpi_field) + 1
    finally:
        db.session.rollback()


def test_reinspeccion_oficio_generica_suma_universo_oficio(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        _cierre_oficio_hibrido("REINSPECCION")
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.reinspecciones_oficio_realizadas == antes.kpis.reinspecciones_oficio_realizadas + 1
        assert out.kpis.ratificaciones_clausura_realizadas == antes.kpis.ratificaciones_clausura_realizadas
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "tipo_iniciador,kpi_field",
    [
        ("RATIFICACION_CLAUSURA_OFICIO", "ratificaciones_clausura_realizadas"),
        ("RATIFICACION_DECOMISO_OFICIO", "ratificaciones_decomiso_realizadas"),
        ("VERIFICAR_INFORMAR_OFICIO", "verificar_informar_realizadas"),
    ],
)
def test_enum_directo_suma_universo_oficio(app_ctx, tipo_iniciador, kpi_field) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion(_FECHA, domicilio_id=dom.id, tipo="REINSPECCION")
        vincular_cierre_realizado(act, _FECHA, tipo_iniciador=tipo_iniciador)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.reinspecciones_oficio_realizadas == antes.kpis.reinspecciones_oficio_realizadas + 1
        assert getattr(out.kpis, kpi_field) == getattr(antes.kpis, kpi_field) + 1
    finally:
        db.session.rollback()


def test_no_realizada_no_suma_reinspecciones_oficio(app_ctx) -> None:
    from tests.indicadores_cierre_fixtures import vincular_cierre_no_realizado

    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion(_FECHA, domicilio_id=dom.id, tipo="REINSPECCION")
        vincular_cierre_no_realizado(
            act,
            _FECHA,
            tipo_iniciador="REINSPECCION_OFICIO",
            contraproducencia="LOCAL_CERRADO",
        )
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.reinspecciones_oficio_realizadas == antes.kpis.reinspecciones_oficio_realizadas
    finally:
        db.session.rollback()
