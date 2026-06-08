"""
Base canónica de «actuación realizada» para indicadores del dashboard (D1d.11fix-a).
"""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.indicadores.services.indicadores_ejecutivo_service import (
    build_indicadores_ejecutivo,
)
from app.domains.indicadores.services.indicadores_operativos_queries import (
    canonical_tipo_iniciador,
    loose_key_tipo_operativo,
)
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
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
    Motivo,
    OrdenTrabajo,
    Rubro,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_DESDE = date(2099, 6, 1)
_HASTA = date(2099, 6, 30)
_FECHA = date(2099, 6, 15)


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


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"u_real_{suf}",
        email=f"real_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_inspector() -> Inspector:
    turno = Turno.query.first()
    if turno is None:
        turno = Turno(turno=TipoTurno.MANIANA)
        db.session.add(turno)
        db.session.flush()
    ins = Inspector(nombre=_unique_name("InspReal"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_actuacion_cruda(fecha: date, domicilio_id: int | None = None) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=fecha.year, mes=fecha.month)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=fecha.month,
        anio=fecha.year,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=domicilio_id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_domicilio_con_rubro(nombre_rubro: str | None = None) -> Domicilio:
    rub = Rubro.query.first()
    if rub is None:
        rub = Rubro(nombre=nombre_rubro or _unique_name("RubReal"))
        db.session.add(rub)
        db.session.flush()
    c = Contribuyente(apellido="Real", nombre="T", documento=str(random.randint(10_000_000, 99_999_999)))
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CalleReal"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
    )
    db.session.add(dom)
    db.session.flush()
    return dom


def test_actuacion_cruda_sin_cierre_no_cuenta_realizada(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas
    finally:
        db.session.rollback()


def test_ruta_item_realizado_con_actuacion_cuenta(app_ctx) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        vincular_cierre_realizado(act, _FECHA)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert out.kpis.actuaciones_realizadas == antes.kpis.actuaciones_realizadas + 1
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "tipo_canonico,kpi_field",
    [
        ("RATIFICACION_DECOMISO_OFICIO", "ratificaciones_decomiso_realizadas"),
        ("RATIFICACION_CLAUSURA_OFICIO", "ratificaciones_clausura_realizadas"),
        ("VERIFICAR_INFORMAR_OFICIO", "verificar_informar_realizadas"),
        ("REINSPECCION_NOTIFICACION", "reinspecciones_notificacion_realizadas"),
    ],
)
def test_kpi_tipo_iniciador_realizado_cuenta(app_ctx, tipo_canonico, kpi_field) -> None:
    try:
        antes = build_indicadores_ejecutivo(_DESDE, _HASTA)
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        vincular_cierre_realizado(act, _FECHA, tipo_iniciador=tipo_canonico)
        db.session.flush()
        out = build_indicadores_ejecutivo(_DESDE, _HASTA)
        assert getattr(out.kpis, kpi_field) == getattr(antes.kpis, kpi_field) + 1
    finally:
        db.session.rollback()


@pytest.mark.parametrize(
    "tipo_variante,tipo_canonico",
    [
        ("RATIFICACION_DECOMISO_OFICIO", "RATIFICACION_DECOMISO_OFICIO"),
        ("Ratificación de decomiso", "RATIFICACION_DECOMISO_OFICIO"),
        ("ratificacion de clausura", "RATIFICACION_CLAUSURA_OFICIO"),
        ("Verificar e informar", "VERIFICAR_INFORMAR_OFICIO"),
        ("ratificacionDecomiso", "RATIFICACION_DECOMISO_OFICIO"),
        ("REINSPECCION_NOTIFICACION", "REINSPECCION_NOTIFICACION"),
    ],
)
def test_normaliza_variantes_tipo_iniciador(tipo_variante, tipo_canonico) -> None:
    assert canonical_tipo_iniciador(tipo_variante) == tipo_canonico


def test_loose_key_normaliza_variantes_tipo() -> None:
    assert canonical_tipo_iniciador("RATIFICACION_DECOMISO") == "RATIFICACION_DECOMISO_OFICIO"
    assert canonical_tipo_iniciador("ratificación de decomiso") == "RATIFICACION_DECOMISO_OFICIO"
    assert loose_key_tipo_operativo("RATIFICACION_CLAUSURA") == loose_key_tipo_operativo(
        "ratificacion clausura"
    )


def test_top_rubros_solo_realizadas(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubroSoloReal")
        rub = Rubro(nombre=rub_nombre)
        db.session.add(rub)
        db.session.flush()
        dom = Domicilio(calle=_unique_name("CR"), numero="1", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        cruda = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        m = Motivo.query.first()
        if m is None:
            m = Motivo(nombre=_unique_name("MotReal"))
            db.session.add(m)
            db.session.flush()
        attach_notificacion(cruda, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})

        realizada = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        vincular_cierre_realizado(realizada, _FECHA)
        db.session.flush()

        out = build_indicadores_riesgo(_DESDE, _HASTA)
        rubros = {r.rubro: r.cantidad for r in out.top_rubros}
        assert rubros.get(rub_nombre, 0) == 1
    finally:
        db.session.rollback()


def test_top_rubros_no_cuenta_no_realizadas_ni_crudas(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubNoCuenta")
        rub = Rubro(nombre=rub_nombre)
        db.session.add(rub)
        db.session.flush()
        dom = Domicilio(calle=_unique_name("CNR"), numero="3", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        cruda = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        no_real = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        vincular_cierre_no_realizado(no_real, _FECHA)
        db.session.flush()

        out = build_indicadores_riesgo(_DESDE, _HASTA)
        rubros = {r.rubro: r.cantidad for r in out.top_rubros}
        assert rubros.get(rub_nombre, 0) == 0
        assert cruda.id  # actuación cruda sin cierre tampoco debe sumar
    finally:
        db.session.rollback()


def test_motivos_notificacion_desde_realizadas(app_ctx) -> None:
    try:
        nombre = _unique_name("MotSoloReal")
        m = Motivo(nombre=nombre)
        db.session.add(m)
        db.session.flush()
        dom = _mk_domicilio_con_rubro()
        cruda = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        attach_notificacion(cruda, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        realizada = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        attach_notificacion(realizada, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        vincular_cierre_realizado(realizada, _FECHA)
        db.session.flush()

        out = build_indicadores_riesgo(_DESDE, _HASTA)
        counts = {r.motivo: r.cantidad for r in out.top_motivos_notificacion}
        assert counts.get(nombre, 0) == 1
    finally:
        db.session.rollback()


def test_decomiso_kg_por_rubro_solo_realizadas(app_ctx) -> None:
    try:
        rub_nombre = _unique_name("RubKgReal")
        rub = Rubro(nombre=rub_nombre)
        db.session.add(rub)
        db.session.flush()
        dom = Domicilio(calle=_unique_name("CK"), numero="2", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        cruda = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        attach_decomiso(cruda, {"acta_num": _unique_ot_num(), "kilos_total": 99})
        realizada = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        attach_decomiso(realizada, {"acta_num": _unique_ot_num(), "kilos_total": 12.5})
        vincular_cierre_realizado(realizada, _FECHA)
        db.session.flush()

        out = build_indicadores_riesgo(_DESDE, _HASTA)
        by_rubro = {r.rubro: r.kg for r in out.decomiso_kg_por_rubro}
        assert abs(by_rubro.get(rub_nombre, 0) - 12.5) < 0.01
    finally:
        db.session.rollback()


def test_filtro_distrito_id_sobre_base_realizada(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos.")
        d_a, d_b = distritos[0], distritos[1]
        if d_a.id == d_b.id:
            pytest.skip("Se requieren 2 distritos distintos.")

        dom_a = Domicilio(calle=_unique_name("DA"), numero="1", distrito_id=d_a.id)
        dom_b = Domicilio(calle=_unique_name("DB"), numero="2", distrito_id=d_b.id)
        db.session.add_all([dom_a, dom_b])
        db.session.flush()

        act_a = _mk_actuacion_cruda(_FECHA, domicilio_id=dom_a.id)
        vincular_cierre_realizado(act_a, _FECHA)
        act_b = _mk_actuacion_cruda(_FECHA, domicilio_id=dom_b.id)
        vincular_cierre_realizado(act_b, _FECHA)
        db.session.flush()

        out_a = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_a.id)
        out_b = build_indicadores_ejecutivo(_DESDE, _HASTA, distrito_id=d_b.id)
        assert out_a.kpis.actuaciones_realizadas >= 1
        assert out_b.kpis.actuaciones_realizadas >= 1
    finally:
        db.session.rollback()


def test_filtro_inspector_id_sin_duplicar(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        dom = _mk_domicilio_con_rubro()
        act = _mk_actuacion_cruda(_FECHA, domicilio_id=dom.id)
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=ins.id,
            )
        )
        vincular_cierre_realizado(act, _FECHA, inspector_id=ins.id)
        db.session.flush()

        out = build_indicadores_ejecutivo(_DESDE, _HASTA, inspector_id=ins.id)
        assert out.kpis.actuaciones_realizadas == 1
    finally:
        db.session.rollback()


def test_resumen_sigue_funcionando(app_ctx) -> None:
    try:
        build_indicadores_resumen(date(2026, 1, 1), date(2026, 12, 31))
    finally:
        db.session.rollback()


def test_contratos_ejecutivo_sin_cambios(client, auth_headers) -> None:
    resp = client.get(
        "/api/indicadores/ejecutivo?desde=2099-06-01&hasta=2099-06-30",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in (
        "periodo",
        "kpis",
        "actas_por_tipo",
    ):
        assert key in data
