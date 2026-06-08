"""
D1d.11fix-a4 — Período operativo por RutaTrabajo.fecha (no ejecutado_at).
"""

from __future__ import annotations

import random
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from tests.indicadores_cierre_fixtures import (
    vincular_cierre_no_realizado,
    vincular_cierre_realizado,
    vincular_ruta_en_proceso,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Domicilio,
    Inspector,
    Motivo,
    OrdenTrabajo,
    Rubro,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_JUNIO_DESDE = date(2099, 6, 1)
_JUNIO_HASTA = date(2099, 6, 30)
_MAYO = date(2099, 5, 15)
_JUNIO = date(2099, 6, 15)
_JULIO_EJEC = date(2099, 7, 10)


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


def _mk_domicilio() -> Domicilio:
    rub = Rubro(nombre=_unique_name("RubA4"))
    db.session.add(rub)
    db.session.flush()
    c = Contribuyente(apellido="A4", nombre="T", documento=str(random.randint(10_000_000, 99_999_999)))
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=_unique_name("CA4"), numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    return dom


def _mk_actuacion(domicilio_id: int, *, tipo: str = "INSPECCION") -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2099, mes=6)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=_JUNIO,
        mes=6,
        anio=2099,
        tipo=tipo,
        orden_trabajo_id=ot.id,
        domicilio_id=domicilio_id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_inspector() -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(nombre=_unique_name("InsA4"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def test_mayo_cerrado_en_junio_no_cuenta_junio(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_realizado(
            act, _MAYO, fecha_ruta=_MAYO, fecha_ejecutado=datetime(2099, 6, 2, 16, 0, 0)
        )
        db.session.flush()
        out = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas
        mayo = build_indicadores_ejecutivo(date(2099, 5, 1), date(2099, 5, 31))
        assert mayo.kpis.actuaciones_realizadas >= antes.kpis.actuaciones_realizadas + 1
    finally:
        db.session.rollback()


def test_junio_cerrado_en_junio_cuenta_junio(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_realizado(act, _JUNIO, fecha_ruta=_JUNIO, fecha_ejecutado=_JUNIO)
        db.session.flush()
        out = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas + 1
    finally:
        db.session.rollback()


def test_junio_cerrado_en_julio_cuenta_junio(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_realizado(
            act, _JUNIO, fecha_ruta=_JUNIO, fecha_ejecutado=_JULIO_EJEC
        )
        db.session.flush()
        out = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas + 1
    finally:
        db.session.rollback()


def test_junio_en_proceso_no_cuenta_realizada(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_ruta_en_proceso(act, _JUNIO)
        db.session.flush()
        out = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas
    finally:
        db.session.rollback()


def test_junio_local_cerrado_pendiente_cuenta_no_realizadas(app_ctx) -> None:
    try:
        antes = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_no_realizado(
            act, _JUNIO, fecha_ruta=_JUNIO, contraproducencia="LOCAL CERRADO"
        )
        db.session.flush()
        out = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.por_tipo.inspeccion == antes.por_tipo.inspeccion + 1
    finally:
        db.session.rollback()


def test_junio_no_realizado_cuenta_no_realizadas(app_ctx) -> None:
    try:
        antes = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_no_realizado(
            act, _JUNIO, fecha_ruta=_JUNIO, contraproducencia="NO_EXISTE_LOCAL"
        )
        db.session.flush()
        out = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.por_tipo.inspeccion == antes.por_tipo.inspeccion + 1
    finally:
        db.session.rollback()


def test_mayo_no_realizado_no_cuenta_junio(app_ctx) -> None:
    try:
        antes = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_no_realizado(
            act,
            _MAYO,
            fecha_ruta=_MAYO,
            fecha_ejecutado=datetime(2099, 6, 2, 16, 0, 0),
            contraproducencia="NO_EXISTE_LOCAL",
        )
        db.session.flush()
        out = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.por_tipo.inspeccion == antes.por_tipo.inspeccion
        mayo = build_indicadores_no_realizadas(date(2099, 5, 1), date(2099, 5, 31))
        assert mayo.por_tipo.inspeccion >= antes.por_tipo.inspeccion + 1
    finally:
        db.session.rollback()


def test_junio_no_realizado_cerrado_julio_cuenta_junio(app_ctx) -> None:
    try:
        antes = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_no_realizado(
            act,
            _JUNIO,
            fecha_ruta=_JUNIO,
            fecha_ejecutado=_JULIO_EJEC,
            contraproducencia="NO_EXISTE_LOCAL",
        )
        db.session.flush()
        out = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.por_tipo.inspeccion == antes.por_tipo.inspeccion + 1
        top = {r.contraproducencia: r.cantidad for r in out.top_contraproducencias}
        assert top.get("No existe local", 0) >= 1
    finally:
        db.session.rollback()


def test_junio_en_proceso_no_cuenta_no_realizadas(app_ctx) -> None:
    try:
        antes = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        act.contraproducencia = "LOCAL CERRADO"
        vincular_ruta_en_proceso(act, _JUNIO)
        db.session.flush()
        out = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.por_tipo.inspeccion == antes.por_tipo.inspeccion
    finally:
        db.session.rollback()


def test_productividad_no_realizada_usa_fecha_ruta(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id, inspector_id=ins.id
            )
        )
        vincular_cierre_no_realizado(
            act,
            _JUNIO,
            fecha_ruta=_JUNIO,
            fecha_ejecutado=_JULIO_EJEC,
            contraproducencia="NO_EXISTE_LOCAL",
            inspector_id=ins.id,
        )
        db.session.flush()
        nr = build_indicadores_no_realizadas(_JUNIO_DESDE, _JUNIO_HASTA, inspector_id=ins.id)
        prod = build_indicadores_productividad(_JUNIO_DESDE, _JUNIO_HASTA, inspector_id=ins.id)
        rows = [r for r in prod.inspectores_no_realizadas if r.inspector_id == ins.id]
        assert len(rows) == 1
        assert rows[0].total_no_realizadas == nr.por_tipo.inspeccion
        assert rows[0].total_no_realizadas >= 1
    finally:
        db.session.rollback()


def test_ejecutivo_riesgo_no_cambian_con_no_realizada(app_ctx) -> None:
    try:
        ej_antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        ri_antes = build_indicadores_riesgo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        vincular_cierre_no_realizado(
            act, _JUNIO, fecha_ruta=_JUNIO, contraproducencia="NO_EXISTE_LOCAL"
        )
        db.session.flush()
        ej_desp = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        ri_desp = build_indicadores_riesgo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert ej_desp.kpis.actuaciones_realizadas == ej_antes.kpis.actuaciones_realizadas
        assert ej_desp.kpis.actas_labradas == ej_antes.kpis.actas_labradas
        assert ri_desp.top_rubros == ri_antes.top_rubros
        assert ri_desp.top_motivos_notificacion == ri_antes.top_motivos_notificacion
    finally:
        db.session.rollback()


def test_actas_mayo_ruta_no_suman_junio(app_ctx) -> None:
    try:
        dom = _mk_domicilio()
        m = Motivo(nombre=_unique_name("MotA4"))
        db.session.add(m)
        db.session.flush()
        act = _mk_actuacion(dom.id)
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        vincular_cierre_realizado(
            act, _MAYO, fecha_ruta=_MAYO, fecha_ejecutado=datetime(2099, 6, 3, 15, 0, 0)
        )
        db.session.flush()
        junio = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        mayo = build_indicadores_ejecutivo(date(2099, 5, 1), date(2099, 5, 31))
        assert junio.actas_por_tipo.notificacion == 0
        assert mayo.actas_por_tipo.notificacion >= 1
    finally:
        db.session.rollback()


def test_top_rubros_solo_rutas_junio_realizadas(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubJunA4")
        rub = Rubro(nombre=rub_nombre)
        db.session.add(rub)
        db.session.flush()
        dom_j = Domicilio(calle=_unique_name("DJ"), numero="1", rubro_id=rub.id)
        dom_m = Domicilio(calle=_unique_name("DM"), numero="2", rubro_id=rub.id)
        db.session.add_all([dom_j, dom_m])
        db.session.flush()
        act_j = _mk_actuacion(dom_j.id)
        act_m = _mk_actuacion(dom_m.id)
        vincular_cierre_realizado(act_j, _JUNIO, fecha_ruta=_JUNIO)
        vincular_cierre_realizado(
            act_m, _MAYO, fecha_ruta=_MAYO, fecha_ejecutado=datetime(2099, 6, 2, 10, 0, 0)
        )
        db.session.flush()
        out = build_indicadores_riesgo(_JUNIO_DESDE, _JUNIO_HASTA)
        rubros = {r.rubro: r.cantidad for r in out.top_rubros}
        assert rubros.get(rub_nombre, 0) == 1
    finally:
        db.session.rollback()


def test_motivos_junio_solo_rutas_junio(app_ctx) -> None:
    try:
        nombre = _unique_name("MotJunA4")
        m = Motivo(nombre=nombre)
        db.session.add(m)
        db.session.flush()
        dom_j = _mk_domicilio()
        dom_m = _mk_domicilio()
        act_j = _mk_actuacion(dom_j.id)
        act_m = _mk_actuacion(dom_m.id)
        attach_notificacion(act_j, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        attach_notificacion(act_m, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        vincular_cierre_realizado(act_j, _JUNIO, fecha_ruta=_JUNIO)
        vincular_cierre_realizado(
            act_m, _MAYO, fecha_ruta=_MAYO, fecha_ejecutado=datetime(2099, 6, 2, 10, 0, 0)
        )
        db.session.flush()
        out = build_indicadores_riesgo(_JUNIO_DESDE, _JUNIO_HASTA)
        counts = {x.motivo: x.cantidad for x in out.top_motivos_notificacion}
        assert counts.get(nombre, 0) == 1
    finally:
        db.session.rollback()


def test_productividad_realizada_usa_fecha_ruta(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id)
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id, inspector_id=ins.id
            )
        )
        vincular_cierre_realizado(
            act, _JUNIO, fecha_ruta=_JUNIO, inspector_id=ins.id
        )
        db.session.flush()
        out = build_indicadores_productividad(_JUNIO_DESDE, _JUNIO_HASTA)
        rows = [r for r in out.inspectores_realizadas if r.inspector_id == ins.id]
        assert len(rows) == 1
        assert rows[0].total_realizadas == 1
    finally:
        db.session.rollback()


def test_bucket_hibrido_ratificacion_con_fecha_ruta(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        dom = _mk_domicilio()
        act = _mk_actuacion(dom.id, tipo="RATIFICACION DE CLAUSURA")
        vincular_cierre_realizado(
            act,
            _JUNIO,
            fecha_ruta=_JUNIO,
            tipo_iniciador="REINSPECCION_OFICIO",
        )
        db.session.flush()
        out = build_indicadores_ejecutivo(_JUNIO_DESDE, _JUNIO_HASTA)
        assert out.kpis.ratificaciones_clausura_realizadas == (
            antes.kpis.ratificaciones_clausura_realizadas + 1
        )
    finally:
        db.session.rollback()
