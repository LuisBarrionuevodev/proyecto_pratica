"""
GET /api/indicadores/no-realizadas: agregaciones reales por tipo, contraproducencias y distritos.
"""

from __future__ import annotations

import random
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.database import db
from sqlalchemy import func

from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    _no_realizadas_administrativas_base_query,
    _no_realizadas_base_query,
    format_contraproducencia_label,
    is_contraproducencia_excluida_valor,
)
from app.domains.indicadores.services.indicadores_no_realizadas_service import (
    build_indicadores_no_realizadas,
)
from app.domains.indicadores.services.indicadores_resumen_service import build_indicadores_resumen
from tests.helpers.fixture_isolation import uniq_ruta_numero, unique_ot_numero
from tests.indicadores_cierre_fixtures import estado_iniciador_tras_no_realizado
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    Turno,
    User,
    actuaciones_inspector,
)
from app.models.turno import TipoTurno

_DESDE = date(2026, 7, 1)
_HASTA = date(2026, 7, 31)
_QUERY_OK = "desde=2026-07-01&hasta=2026-07-31"


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


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"u_nr_{suf}",
        email=f"nr_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_no_realizada(
    tipo_iniciador: str,
    contraproducencia: str,
    fecha_cierre: date,
    *,
    distrito_id: int | None = None,
    inspector_id: int | None = None,
    estado_iniciador: str | None = None,
) -> tuple[RutaItem, Actuaciones]:
    """
    Cierre NO_REALIZADO; por defecto el estado del iniciador sigue Completar trabajo.
    """
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere al menos un rubro en catálogo")
    u = _mk_user()
    doc = str(random.randint(10_000_000, 40_000_000))
    c = Contribuyente(apellido="NR", nombre="T", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(
        calle=_unique_name("CalleNR"),
        numero="1",
        rubro_id=rub.id,
        contribuyente_id=c.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_ot_num(), anio=2026, mes=7)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_cierre,
        mes=7,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        contraproducencia=contraproducencia,
    )
    db.session.add(act)
    db.session.flush()
    if inspector_id is not None:
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act.id,
                inspector_id=inspector_id,
            )
        )
    ini_estado = (
        estado_iniciador
        if estado_iniciador is not None
        else estado_iniciador_tras_no_realizado(contraproducencia)
    )
    ini = IniciadorRuta(
        tipo_iniciador=tipo_iniciador,
        estado_iniciador=ini_estado,
        fecha_origen=fecha_cierre,
        anio=2026,
        mes=7,
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
        numero=uniq_ruta_numero(),
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="FINALIZADO",
        estado_ejecucion="NO_REALIZADO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
        ejecutado_at=datetime(2026, 7, 15, 12, 0, 0),
        ejecutado_por_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    return item, act


def _por_tipo_dict(out):
    pt = out.por_tipo
    return {
        "inspeccion": pt.inspeccion,
        "reinspeccion_oficio": pt.reinspeccion_oficio,
        "reinspeccion_notificacion": pt.reinspeccion_notificacion,
        "denuncia": pt.denuncia,
    }


@pytest.mark.parametrize(
    "tipo_iniciador,bucket",
    [
        ("RELEVAMIENTO", "inspeccion"),
        ("REINSPECCION_OFICIO", "reinspeccion_oficio"),
        ("RATIFICACION_CLAUSURA_OFICIO", "reinspeccion_oficio"),
        ("RATIFICACION_DECOMISO_OFICIO", "reinspeccion_oficio"),
        ("VERIFICAR_INFORMAR_OFICIO", "reinspeccion_oficio"),
        ("REINSPECCION_NOTIFICACION", "reinspeccion_notificacion"),
        ("DENUNCIA", "denuncia"),
    ],
)
def test_por_tipo_suma_por_iniciador(app_ctx, tipo_iniciador, bucket) -> None:
    try:
        before = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        _mk_no_realizada(tipo_iniciador, "LOCAL_CERRADO", date(2026, 7, 15))
        db.session.flush()
        after = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        assert after[bucket] == before[bucket] + 1
    finally:
        db.session.rollback()


def test_estado_canonico_finalizado_no_realizado_cuenta(app_ctx) -> None:
    """Completar trabajo persiste FINALIZADO+NO_REALIZADO; debe contar en KPI."""
    try:
        before = build_indicadores_no_realizadas(_DESDE, _HASTA).total
        _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 15))
        db.session.flush()
        after = build_indicadores_no_realizadas(_DESDE, _HASTA).total
        assert after == before + 1
    finally:
        db.session.rollback()


def test_estado_legado_no_realizado_sigue_contando(app_ctx) -> None:
    """Ítems legados con eri=NO_REALIZADO siguen en el KPI."""
    try:
        before = build_indicadores_no_realizadas(_DESDE, _HASTA).total
        item, _act = _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 15))
        item.estado_ruta_item = "NO_REALIZADO"
        item.estado_ejecucion = "NO_REALIZADO"
        db.session.flush()
        after = build_indicadores_no_realizadas(_DESDE, _HASTA).total
        assert after == before + 1
    finally:
        db.session.rollback()


def test_bucket_no_existe_direccion_incorrecta(app_ctx) -> None:
    try:
        _mk_no_realizada("RELEVAMIENTO", "DIRECCION INCORRECTA", date(2026, 7, 15))
        db.session.flush()
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        by_bucket = {r.bucket: r.cantidad for r in out.contraproducencias_resumen}
        assert by_bucket.get("no_existe", 0) >= 1
    finally:
        db.session.rollback()


def test_no_hubo_excluido_de_top_y_por_tipo(app_ctx) -> None:
    try:
        before = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        _mk_no_realizada("RELEVAMIENTO", "NO_HUBO", date(2026, 7, 16))
        db.session.flush()
        after = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        assert after["inspeccion"] == before["inspeccion"]
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        labels = {r.contraproducencia.lower() for r in out.top_contraproducencias}
        assert "no hubo" not in labels
    finally:
        db.session.rollback()


def test_format_contraproducencia_label_normaliza_enum_y_camel(app_ctx) -> None:
    assert format_contraproducencia_label("LOCAL_CERRADO") == "Local cerrado"
    assert format_contraproducencia_label("NO_SE_ENCUENTRA") == "No se encuentra"
    assert format_contraproducencia_label("noSeEncuentra") == "No se encuentra"
    assert is_contraproducencia_excluida_valor("NO_HUBO") is True
    assert is_contraproducencia_excluida_valor("No hubo") is True
    assert is_contraproducencia_excluida_valor(None) is True
    assert is_contraproducencia_excluida_valor("LOCAL_CERRADO") is False


def test_local_cerrado_pendiente_cuenta(app_ctx) -> None:
    try:
        before = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 17))
        db.session.flush()
        after = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        assert after["inspeccion"] == before["inspeccion"] + 1
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        labels = {r.contraproducencia for r in out.top_contraproducencias}
        assert "Local cerrado" in labels
    finally:
        db.session.rollback()


def test_no_existe_local_cerrado_cuenta(app_ctx) -> None:
    try:
        before = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        _mk_no_realizada("RELEVAMIENTO", "NO_EXISTE_LOCAL", date(2026, 7, 18))
        db.session.flush()
        after = _por_tipo_dict(build_indicadores_no_realizadas(_DESDE, _HASTA))
        assert after["inspeccion"] == before["inspeccion"] + 1
    finally:
        db.session.rollback()


def test_top_contraproducencias_incluye_local_cerrado(app_ctx) -> None:
    try:
        _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 17))
        _mk_no_realizada("RELEVAMIENTO", "NO_EXISTE_LOCAL", date(2026, 7, 18))
        _mk_no_realizada("DENUNCIA", "LOCAL_CERRADO", date(2026, 7, 19))
        db.session.flush()
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        by_label = {r.contraproducencia: r.cantidad for r in out.top_contraproducencias}
        assert by_label.get("Local cerrado", 0) >= 2
        assert by_label.get("No existe local", 0) >= 1
    finally:
        db.session.rollback()


def test_helper_administrativo_excluye_reencolables(app_ctx) -> None:
    try:
        _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 20))
        _mk_no_realizada("RELEVAMIENTO", "NO_EXISTE_LOCAL", date(2026, 7, 21))
        db.session.flush()
        operativo = (
            _no_realizadas_base_query(_DESDE, _HASTA)
            .with_entities(func.count(func.distinct(RutaItem.id)))
            .scalar()
            or 0
        )
        administrativo = (
            _no_realizadas_administrativas_base_query(_DESDE, _HASTA)
            .with_entities(func.count(func.distinct(RutaItem.id)))
            .scalar()
            or 0
        )
        assert operativo >= 2
        assert administrativo >= 1
        assert operativo > administrativo
    finally:
        db.session.rollback()


def test_distritos_agrupa_y_sin_distrito(app_ctx) -> None:
    try:
        distritos = Distrito.query.limit(1).all()
        if not distritos:
            pytest.skip("Se requiere al menos un distrito en BD.")
        dist = distritos[0]
        _mk_no_realizada(
            "RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 10), distrito_id=dist.id
        )
        _mk_no_realizada(
            "RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 11), distrito_id=dist.id
        )
        _mk_no_realizada("DENUNCIA", "NO_EXISTE_LOCAL", date(2026, 7, 12), distrito_id=None)
        db.session.flush()
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        by_id = {r.distrito_id: r for r in out.distritos_con_mas_no_realizadas}
        assert dist.id in by_id
        assert by_id[dist.id].cantidad >= 2
        sin = next(
            (r for r in out.distritos_con_mas_no_realizadas if r.distrito_nombre == "Sin distrito"),
            None,
        )
        assert sin is not None
        assert sin.distrito_id == 0
        assert sin.distrito_codigo == "SIN_DISTRITO"
        assert sin.cantidad >= 1
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
        _mk_no_realizada(
            "RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 14), distrito_id=d_a.id
        )
        _mk_no_realizada("DENUNCIA", "LOCAL_CERRADO", date(2026, 7, 14), distrito_id=d_b.id)
        db.session.flush()
        out_a = build_indicadores_no_realizadas(_DESDE, _HASTA, distrito_id=d_a.id)
        assert out_a.por_tipo.inspeccion >= 1
        assert out_a.por_tipo.denuncia == 0
    finally:
        db.session.rollback()


def test_filtro_inspector_id_sin_duplicar(app_ctx) -> None:
    try:
        turno = Turno.query.first()
        if turno is None:
            turno = Turno(turno=TipoTurno.MANIANA)
            db.session.add(turno)
            db.session.flush()
        ins_a = Inspector(nombre=_unique_name("InspA"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
        ins_b = Inspector(nombre=_unique_name("InspB"), legajo=_unique_ot_num()[:5], turno_id=turno.id)
        db.session.add_all([ins_a, ins_b])
        db.session.flush()
        _mk_no_realizada(
            "RELEVAMIENTO",
            "LOCAL_CERRADO",
            date(2026, 7, 13),
            inspector_id=ins_a.id,
        )
        item2, act2 = _mk_no_realizada(
            "RELEVAMIENTO",
            "NO_EXISTE_LOCAL",
            date(2026, 7, 13),
            inspector_id=ins_a.id,
        )
        db.session.execute(
            actuaciones_inspector.insert().values(
                actuaciones_id=act2.id,
                inspector_id=ins_b.id,
            )
        )
        _mk_no_realizada("DENUNCIA", "NO_EXISTE_LOCAL", date(2026, 7, 13))
        db.session.flush()
        out = build_indicadores_no_realizadas(_DESDE, _HASTA, inspector_id=ins_a.id)
        assert out.por_tipo.inspeccion == 2
        assert out.por_tipo.denuncia == 0
        assert item2.id is not None
    finally:
        db.session.rollback()


def test_periodo_vacio_ceros_y_arrays(app_ctx) -> None:
    try:
        out = build_indicadores_no_realizadas(date(2099, 1, 1), date(2099, 1, 31))
        assert out.por_tipo.inspeccion == 0
        assert out.por_tipo.denuncia == 0
        assert out.top_contraproducencias == []
        assert out.distritos_con_mas_no_realizadas == []
    finally:
        db.session.rollback()


def test_contraproducencias_resumen_buckets(app_ctx) -> None:
    try:
        _mk_no_realizada("RELEVAMIENTO", "LOCAL_CERRADO", date(2026, 7, 15))
        _mk_no_realizada("RELEVAMIENTO", "CLIMA", date(2026, 7, 16))
        _mk_no_realizada("DENUNCIA", "NO SE RATIFICÓ", date(2026, 7, 17))
        _mk_no_realizada("RELEVAMIENTO", "ZONA ROJA", date(2026, 7, 18))
        db.session.flush()
        out = build_indicadores_no_realizadas(_DESDE, _HASTA)
        assert out.total >= 4
        by_bucket = {r.bucket: r.cantidad for r in out.contraproducencias_resumen}
        assert by_bucket.get("local_cerrado", 0) >= 1
        assert by_bucket.get("clima", 0) >= 1
        assert by_bucket.get("no_se_ratifico", 0) >= 1
        assert by_bucket.get("otras", 0) >= 1
        assert sum(by_bucket.values()) == out.total
    finally:
        db.session.rollback()


def test_get_api_no_realizadas_200(client, auth_headers) -> None:
    resp = client.get(
        f"/api/indicadores/no-realizadas?{_QUERY_OK}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    for k in ("inspeccion", "reinspeccion_oficio", "reinspeccion_notificacion", "denuncia"):
        assert k in data["por_tipo"]
    assert "total" in data
    assert "contraproducencias_resumen" in data
    assert isinstance(data["contraproducencias_resumen"], list)


def test_resumen_sigue_funcionando(app_ctx, client, auth_headers) -> None:
    try:
        build_indicadores_resumen(date(2026, 1, 1), date(2026, 12, 31))
    finally:
        db.session.rollback()
    resp = client.get(
        "/api/indicadores/resumen?desde=2026-01-01&hasta=2026-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "actuaciones" in (resp.get_json() or {})
