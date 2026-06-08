"""
GET /api/indicadores/productividad: realizadas, no realizadas y actas por inspector.
"""

from __future__ import annotations

import random
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.services.previas_service import resolver_previas
from app.domains.indicadores.services.indicadores_productividad_queries import (
    format_contraproducencia_label,
    principal_bucket_label,
)
from app.domains.indicadores.services.indicadores_productividad_service import (
    build_indicadores_productividad,
)
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from tests.indicadores_cierre_fixtures import (
    estado_iniciador_tras_no_realizado,
    vincular_cierre_realizado,
)
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Motivo,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_DESDE = date(2026, 8, 1)
_HASTA = date(2026, 8, 31)
_FECHA = date(2026, 8, 15)


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
        username=f"u_prod_{suf}",
        email=f"prod_{suf}@t.local",
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
    ins = Inspector(
        nombre=_unique_name("InspProd"),
        legajo=_unique_ot_num()[:5],
        turno_id=turno.id,
    )
    db.session.add(ins)
    db.session.flush()
    return ins


def _mk_visita_cierre(
    tipo_iniciador: str,
    fecha_cierre: date,
    *,
    realizada: bool = True,
    contraproducencia: str | None = None,
    inspector_id: int | None = None,
    distrito_id: int | None = None,
) -> tuple[RutaItem, Actuaciones, Inspector | None]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = _mk_user()
    ins = None
    if inspector_id is None:
        ins = _mk_inspector()
        inspector_id = ins.id
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Prod", nombre="T", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CalleProd"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_cierre,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        contraproducencia=contraproducencia,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    ini_estado = "CUMPLIDO" if realizada else estado_iniciador_tras_no_realizado(
        contraproducencia or "LOCAL_CERRADO"
    )
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador=ini_estado,
        fecha_origen=fecha_cierre,
        anio=2026,
        mes=8,
        domicilio_id=dom.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fecha_cierre,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()
    if realizada:
        estado_ruta = "FINALIZADO"
        estado_ej = "REALIZADO"
    else:
        estado_ruta = "NO_REALIZADO"
        estado_ej = "NO_REALIZADO"
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item=estado_ruta,
        estado_ejecucion=estado_ej,
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=datetime(2026, 8, 15, 10, 0, 0),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    if ins is None and inspector_id is not None:
        ins = db.session.get(Inspector, inspector_id)
    return item, act, ins


def _mk_actuacion_con_inspector(
    fecha: date,
    inspector_id: int,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    return act


def _find_realizada(inspector_id: int, rows):
    return next((r for r in rows if r.inspector_id == inspector_id), None)


@pytest.mark.parametrize(
    "tipo_iniciador,field",
    [
        ("RELEVAMIENTO", "inspecciones"),
        ("REINSPECCION_OFICIO", "reinspecciones_oficio"),
        ("REINSPECCION_NOTIFICACION", "reinspecciones_notificacion"),
        ("DENUNCIA", "denuncias"),
    ],
)
def test_realizada_suma_por_tipo(app_ctx, tipo_iniciador, field) -> None:
    try:
        _, _, ins = _mk_visita_cierre(tipo_iniciador, _FECHA, realizada=True)
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_realizadas)
        assert row is not None
        assert getattr(row, field) >= 1
        assert row.total_realizadas >= getattr(row, field)
    finally:
        db.session.rollback()


def test_no_realizada_suma_y_contraproducencia_principal(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="LOCAL_CERRADO",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas >= 1
        assert row.inspecciones >= 1
        assert row.contraproducencia_principal == "Local cerrado"
    finally:
        db.session.rollback()


def test_no_existe_local_suma_productividad(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=False,
            contraproducencia="NO_EXISTE_LOCAL",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is not None
        assert row.total_no_realizadas >= 1
        assert row.contraproducencia_principal == "No existe local"
    finally:
        db.session.rollback()


def test_no_hubo_no_suma(app_ctx) -> None:
    try:
        _, _, ins = _mk_visita_cierre(
            "DENUNCIA",
            _FECHA,
            realizada=False,
            contraproducencia="NO_HUBO",
        )
        assert ins is not None
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = _find_realizada(ins.id, out.inspectores_no_realizadas)
        assert row is None
    finally:
        db.session.rollback()


def test_principal_bucket_label_empate_prioridad() -> None:
    assert principal_bucket_label(
        {"inspecciones": 2, "reinspecciones_oficio": 2, "denuncias": 0, "reinspecciones_notificacion": 0}
    ) == "Inspección"
    assert format_contraproducencia_label("DOMICILIO_INCORRECTO") == "Domicilio incorrecto"


def _actuacion_con_cierre(inspector_id: int, fecha: date) -> Actuaciones:
    """Actuación con domicilio, inspector y cierre REALIZADO en fecha."""
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="Actas", nombre="T", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=_unique_name("CalleActas"), numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=8)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha,
        mes=8,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    db.session.execute(
        actuaciones_inspector.insert().values(
            actuaciones_id=act.id,
            inspector_id=inspector_id,
        )
    )
    vincular_cierre_realizado(act, fecha, inspector_id=inspector_id)
    return act


def test_actas_notificacion_con_motivos(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        m = Motivo.query.first()
        if m is None:
            m = Motivo(nombre=_unique_name("MotProd"))
            db.session.add(m)
            db.session.flush()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        attach_notificacion(act, {"acta_num": _unique_ot_num(), "motivos": [m.nombre]})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.notificacion >= 1
        assert row.total_actas >= 1
    finally:
        db.session.rollback()


def test_actas_comprobacion_pendiente_no_suma(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        resolver_previas(
            act,
            {"comprobacion_previa_num": _unique_ot_num(), "comprobacion_previa_motivo": None},
        )
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is None or row.comprobacion == 0
    finally:
        db.session.rollback()


def test_actas_comprobacion_labrada(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act = _actuacion_con_cierre(ins.id, _FECHA)
        attach_comprobacion(act, {"acta_num": _unique_ot_num(), "motivo": "Falta higiene"})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.comprobacion >= 1
    finally:
        db.session.rollback()


def test_actas_clausura_y_decomiso(app_ctx) -> None:
    try:
        ins = _mk_inspector()
        act_c = _actuacion_con_cierre(ins.id, _FECHA)
        attach_clausura(act_c, {"acta_num": _unique_ot_num()})
        act_d = _actuacion_con_cierre(ins.id, date(2026, 8, 16))
        attach_decomiso(act_d, {"acta_num": _unique_ot_num(), "kilos_total": 5})
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA)
        row = next((r for r in out.actas_por_inspector if r.inspector_id == ins.id), None)
        assert row is not None
        assert row.clausura >= 1
        assert row.decomiso >= 1
        assert row.total_actas >= 2
    finally:
        db.session.rollback()


def test_filtro_inspector_id(app_ctx) -> None:
    try:
        ins_a = _mk_inspector()
        ins_b = _mk_inspector()
        _mk_visita_cierre("RELEVAMIENTO", _FECHA, realizada=True, inspector_id=ins_a.id)
        _mk_visita_cierre("DENUNCIA", _FECHA, realizada=True, inspector_id=ins_b.id)
        db.session.flush()
        out = build_indicadores_productividad(_DESDE, _HASTA, inspector_id=ins_a.id)
        ids = {r.inspector_id for r in out.inspectores_realizadas}
        assert ids <= {ins_a.id}
        assert ins_a.id in ids
        assert ins_b.id not in ids
    finally:
        db.session.rollback()


def test_filtro_distrito_id(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(2).all()
        if len(distritos) < 2:
            pytest.skip("Se requieren al menos 2 distritos.")
        d_a, d_b = distritos[0], distritos[1]
        if d_a.id == d_b.id:
            pytest.skip("Se requieren 2 distritos distintos.")
        ins = _mk_inspector()
        _mk_visita_cierre(
            "RELEVAMIENTO",
            _FECHA,
            realizada=True,
            inspector_id=ins.id,
            distrito_id=d_a.id,
        )
        _mk_visita_cierre(
            "DENUNCIA",
            _FECHA,
            realizada=True,
            inspector_id=ins.id,
            distrito_id=d_b.id,
        )
        db.session.flush()
        out_a = build_indicadores_productividad(_DESDE, _HASTA, distrito_id=d_a.id)
        row = _find_realizada(ins.id, out_a.inspectores_realizadas)
        assert row is not None
        assert row.inspecciones >= 1
        assert row.denuncias == 0
    finally:
        db.session.rollback()


def test_periodo_vacio_arrays(app_ctx) -> None:
    try:
        out = build_indicadores_productividad(date(2099, 1, 1), date(2099, 1, 31))
        assert out.inspectores_realizadas == []
        assert out.inspectores_no_realizadas == []
        assert out.actas_por_inspector == []
    finally:
        db.session.rollback()


def test_get_api_productividad_200(client, auth_headers) -> None:
    resp = client.get(
        "/api/indicadores/productividad?desde=2026-08-01&hasta=2026-08-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for key in ("inspectores_realizadas", "inspectores_no_realizadas", "actas_por_inspector"):
        assert key in data
        assert isinstance(data[key], list)


def test_resumen_sigue_funcionando(app_ctx) -> None:
    try:
        build_indicadores_resumen(date(2026, 1, 1), date(2026, 12, 31))
    finally:
        db.session.rollback()
