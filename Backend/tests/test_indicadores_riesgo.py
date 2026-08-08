"""
GET /api/indicadores/riesgo y agregaciones de motivos / decomiso por rubro.
"""

from __future__ import annotations

from datetime import date

import pytest

from tests.helpers.fixture_isolation import unique_ot_numero

from app.database import db
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from tests.indicadores_cierre_fixtures import vincular_cierre_realizado
from app.models import (
    Actuaciones,
    Distrito,
    Domicilio,
    Inspector,
    Motivo,
    OrdenTrabajo,
    Rubro,
    Turno,
)
from app.models.turno import TipoTurno


def _unique_ot_num() -> str:
    return unique_ot_numero()


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{_unique_ot_num()}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


_FECHA = date(2026, 3, 15)
_PERIODO_DESDE = date(2026, 3, 1)
_PERIODO_HASTA = date(2026, 3, 31)


def _mk_actuacion(
    fecha: date | None = None,
    *,
    domicilio_id: int | None = None,
    con_cierre: bool = True,
    tipo_iniciador: str = "RELEVAMIENTO",
    inspector_id: int | None = None,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha or date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        tipo="INSPECCION",
        domicilio_id=domicilio_id,
    )
    db.session.add(act)
    db.session.flush()
    if con_cierre:
        if domicilio_id is None:
            dom = Domicilio(calle=_unique_name("CalleRiesgo"), numero="1")
            db.session.add(dom)
            db.session.flush()
            act.domicilio_id = dom.id
            db.session.flush()
        vincular_cierre_realizado(
            act,
            fecha or _FECHA,
            tipo_iniciador=tipo_iniciador,
            inspector_id=inspector_id,
        )
    return act


def _get_or_create_motivo(nombre: str) -> Motivo:
    m = Motivo.query.filter_by(nombre=nombre).first()
    if m is None:
        m = Motivo(nombre=nombre)
        db.session.add(m)
        db.session.flush()
    return m


def test_riesgo_vacio_periodo_sin_datos(app_ctx) -> None:
    try:
        out = build_indicadores_riesgo(date(2099, 1, 1), date(2099, 1, 31))
        assert out.top_rubros == []
        assert out.top_motivos_notificacion == []
        assert out.top_motivos_comprobacion == []
        assert out.decomiso_kg_por_rubro == []
    finally:
        db.session.rollback()


def test_top_motivos_notificacion_cuenta_motivos_reales(app_ctx) -> None:
    try:
        nombre = _unique_name("CarnetSan")
        m = _get_or_create_motivo(nombre)
        act = _mk_actuacion()
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        labels = [row.motivo for row in out.top_motivos_notificacion]
        assert nombre in labels
        row = next(r for r in out.top_motivos_notificacion if r.motivo == nombre)
        assert row.cantidad >= 1
    finally:
        db.session.rollback()


def test_notificacion_multiples_motivos_cuenta_cada_uno(app_ctx) -> None:
    try:
        m1 = _get_or_create_motivo(_unique_name("MotA"))
        m2 = _get_or_create_motivo(_unique_name("MotB"))
        act = _mk_actuacion()
        attach_notificacion(
            act,
            {"acta_num": _unique_ot_num(), "motivos": [m1.nombre, m2.nombre]},
        )
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        counts = {r.motivo: r.cantidad for r in out.top_motivos_notificacion}
        assert counts.get(m1.nombre, 0) >= 1
        assert counts.get(m2.nombre, 0) >= 1
    finally:
        db.session.rollback()


def test_top_motivos_comprobacion_excluye_pendiente(app_ctx) -> None:
    try:
        act = _mk_actuacion()
        resolver_previas(
            act,
            {
                "comprobacion_previa_num": _unique_ot_num(),
                "comprobacion_previa_motivo": None,
            },
        )
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        motivos = [r.motivo.upper() for r in out.top_motivos_comprobacion]
        assert "PENDIENTE" not in motivos
    finally:
        db.session.rollback()


def test_top_motivos_comprobacion_cuenta_labrada(app_ctx) -> None:
    try:
        motivo_txt = _unique_name("Falta higiene")
        act = _mk_actuacion()
        attach_comprobacion(act, {"acta_num": _unique_ot_num(), "motivo": motivo_txt})
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        assert any(r.motivo == motivo_txt for r in out.top_motivos_comprobacion)
    finally:
        db.session.rollback()


def test_decomiso_kg_por_rubro_suma_correctamente(app_ctx) -> None:
    try:
        rubro_nombre = _unique_name("CarniceriaRiesgo")
        rub = Rubro(nombre=rubro_nombre)
        db.session.add(rub)
        db.session.flush()

        dom = Domicilio(calle=_unique_name("CalleDec"), numero="10", rubro_id=rub.id)
        db.session.add(dom)
        db.session.flush()

        act = _mk_actuacion(domicilio_id=dom.id)
        attach_decomiso(act, {"acta_num": _unique_ot_num(), "kilos_total": 50.5})
        db.session.flush()

        act2 = _mk_actuacion(domicilio_id=dom.id)
        attach_decomiso(act2, {"acta_num": _unique_ot_num(), "kilos_total": 24.5})
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        by_rubro = {r.rubro: r.kg for r in out.decomiso_kg_por_rubro}
        assert abs(by_rubro.get(rubro_nombre, 0) - 75.0) < 0.01
    finally:
        db.session.rollback()


def test_decomiso_sin_rubro_usa_sin_rubro(app_ctx) -> None:
    try:
        dom = Domicilio(calle=_unique_name("SinRubro"), numero="9", rubro_id=None)
        db.session.add(dom)
        db.session.flush()
        act = _mk_actuacion(domicilio_id=dom.id)
        attach_decomiso(act, {"acta_num": _unique_ot_num(), "kilos_total": 10})
        db.session.flush()

        out = build_indicadores_riesgo(_PERIODO_DESDE, _PERIODO_HASTA)
        assert any(r.rubro == "Sin rubro" and r.kg == 10.0 for r in out.decomiso_kg_por_rubro)
    finally:
        db.session.rollback()


def test_filtro_distrito_id_riesgo(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos en BD para este test.")
        dist_a, dist_b = distritos[0], distritos[1]
        if dist_a.id == dist_b.id:
            pytest.skip("Se requieren 2 distritos distintos.")

        dom_a = Domicilio(calle=_unique_name("CA"), numero="1", distrito_id=dist_a.id)
        dom_b = Domicilio(calle=_unique_name("CB"), numero="2", distrito_id=dist_b.id)
        db.session.add_all([dom_a, dom_b])
        db.session.flush()

        m_a = _get_or_create_motivo(_unique_name("SoloDistA"))
        m_b = _get_or_create_motivo(_unique_name("SoloDistB"))
        act_a = _mk_actuacion(domicilio_id=dom_a.id)
        attach_notificacion(act_a, {"acta_num": _unique_ot_num(), "motivos": [m_a.nombre]})
        act_b = _mk_actuacion(domicilio_id=dom_b.id)
        attach_notificacion(act_b, {"acta_num": _unique_ot_num(), "motivos": [m_b.nombre]})
        db.session.flush()

        out_a = build_indicadores_riesgo(
            _PERIODO_DESDE, _PERIODO_HASTA, distrito_id=dist_a.id
        )
        out_b = build_indicadores_riesgo(
            _PERIODO_DESDE, _PERIODO_HASTA, distrito_id=dist_b.id
        )
        labels_a = {r.motivo for r in out_a.top_motivos_notificacion}
        labels_b = {r.motivo for r in out_b.top_motivos_notificacion}
        assert m_a.nombre in labels_a
        assert m_b.nombre not in labels_a
        assert m_b.nombre in labels_b
        assert m_a.nombre not in labels_b
    finally:
        db.session.rollback()


def test_filtro_inspector_id_riesgo(app_ctx) -> None:
    try:
        turno = Turno.query.first()
        if turno is None:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()

        ins = Inspector(nombre=_unique_name("InspRiesgo"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
        db.session.add(ins)
        db.session.flush()

        m = _get_or_create_motivo(_unique_name("SoloInsp"))
        act = _mk_actuacion(inspector_id=ins.id)
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()

        out_ok = build_indicadores_riesgo(
            _PERIODO_DESDE, _PERIODO_HASTA, inspector_id=ins.id
        )
        other_ins = Inspector.query.filter(Inspector.id != ins.id).first()
        if other_ins is None:
            pytest.skip("Se requiere otro inspector en BD para contrastar filtro.")
        out_other = build_indicadores_riesgo(
            _PERIODO_DESDE, _PERIODO_HASTA, inspector_id=other_ins.id
        )
        assert any(r.motivo == m.nombre for r in out_ok.top_motivos_notificacion)
        assert not any(r.motivo == m.nombre for r in out_other.top_motivos_notificacion)
    finally:
        db.session.rollback()


def test_get_indicadores_riesgo_api_schema_completo(client, auth_headers) -> None:
    resp = client.get(
        "/api/indicadores/riesgo?desde=2026-01-01&hasta=2026-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in (
        "top_rubros",
        "top_motivos_notificacion",
        "top_motivos_comprobacion",
        "decomiso_kg_por_rubro",
    ):
        assert key in data
        assert isinstance(data[key], list)
    for item in data.get("top_motivos_notificacion") or []:
        assert "motivo" in item and "cantidad" in item
    for item in data.get("decomiso_kg_por_rubro") or []:
        assert "rubro" in item and "kg" in item


def test_resumen_sigue_ok_despues_riesgo(app_ctx, client, auth_headers) -> None:
    try:
        build_indicadores_resumen(date(2026, 1, 1), date(2026, 12, 31))
    finally:
        db.session.rollback()

    resp = client.get(
        "/api/indicadores/resumen?desde=2026-01-01&hasta=2026-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
