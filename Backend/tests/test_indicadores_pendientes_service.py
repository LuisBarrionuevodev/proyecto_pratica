"""
Regresión de build_indicadores_pendientes (IND-PEND.1): stock actual sin período.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.database import db
from app.domains.indicadores.services.indicadores_pendientes_queries import (
    aggregate_pendientes_stock,
)
from app.domains.indicadores.services.indicadores_pendientes_service import (
    build_indicadores_pendientes,
)
from app.models import IniciadorRuta, User


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ensure_user() -> User:
    u = User.query.filter(User.is_active.is_(True)).first()
    if u:
        return u
    u = User(
        username="pend_ind_test",
        email="pend_ind@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_ini(
    *,
    tipo: str,
    fecha: date,
) -> IniciadorRuta:
    u = _ensure_user()
    ini = IniciadorRuta(
        tipo_iniciador=tipo,
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha,
        anio=fecha.year,
        mes=fecha.month,
        domicilio_id=1,
        prioridad=1,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()
    return ini


def _patch_stock_query(monkeypatch, inis: list[IniciadorRuta]) -> None:
    monkeypatch.setattr(
        "app.domains.indicadores.services.indicadores_pendientes_queries._query_iniciadores_pendientes_stock",
        lambda: list(inis),
    )


def _patch_map_point(monkeypatch, *, distrito_id: int | None = None) -> None:
    def _fake_map(ini: IniciadorRuta, *, distrito_id=None):
        if distrito_id is not None and distrito_id != 99:
            return None
        return {
            "tipo_iniciador": ini.tipo_iniciador,
            "distrito_id": 99,
        }

    monkeypatch.setattr(
        "app.domains.indicadores.services.indicadores_pendientes_queries._map_point_desde_iniciador_backlog",
        _fake_map,
    )


def _kpis_dict(kpis) -> dict[str, int]:
    return {
        "relevamientos_pendientes": kpis.relevamientos_pendientes,
        "reinspecciones_oficio_pendientes": kpis.reinspecciones_oficio_pendientes,
        "reinspecciones_notificacion_pendientes": kpis.reinspecciones_notificacion_pendientes,
        "denuncias_pendientes": kpis.denuncias_pendientes,
        "pendientes_geolocalizacion": kpis.pendientes_geolocalizacion,
    }


def test_sin_pendientes_devuelve_ceros(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [])
    out = build_indicadores_pendientes(date(2099, 1, 1), date(2099, 1, 31))
    assert _kpis_dict(out.kpis) == {
        "relevamientos_pendientes": 0,
        "reinspecciones_oficio_pendientes": 0,
        "reinspecciones_notificacion_pendientes": 0,
        "denuncias_pendientes": 0,
        "pendientes_geolocalizacion": 0,
    }
    assert out.distritos_con_mas_pendientes == []


def test_pendientes_no_cambia_al_variar_periodo(app_ctx, monkeypatch) -> None:
    fecha = date(2026, 5, 10)
    inis = [_mk_ini(tipo="RELEVAMIENTO", fecha=fecha)]
    _patch_stock_query(monkeypatch, inis)
    _patch_map_point(monkeypatch)

    semanal = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 7))
    anual = build_indicadores_pendientes(date(2020, 1, 1), date(2030, 12, 31))
    assert _kpis_dict(semanal.kpis) == _kpis_dict(anual.kpis)
    assert semanal.kpis.relevamientos_pendientes == 1


def test_relevamiento_pendiente_suma_en_kpi(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [_mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 5, 10))])
    _patch_map_point(monkeypatch)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31))
    assert out.kpis.relevamientos_pendientes == 1
    assert out.kpis.denuncias_pendientes == 0


def test_denuncia_pendiente_cuenta_en_contrato_pero_no_en_tabla_distrito(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [_mk_ini(tipo="DENUNCIA", fecha=date(2026, 5, 10))])
    _patch_map_point(monkeypatch)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31))
    assert out.kpis.denuncias_pendientes == 1
    assert out.distritos_con_mas_pendientes == []


def test_reinspeccion_oficio_pendiente_suma_en_kpi(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [_mk_ini(tipo="REINSPECCION_OFICIO", fecha=date(2026, 5, 10))])
    _patch_map_point(monkeypatch)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31))
    assert out.kpis.reinspecciones_oficio_pendientes == 1


def test_reinspeccion_notificacion_pendiente_suma_en_kpi(app_ctx, monkeypatch) -> None:
    _patch_stock_query(
        monkeypatch, [_mk_ini(tipo="REINSPECCION_NOTIFICACION", fecha=date(2026, 5, 10))]
    )
    _patch_map_point(monkeypatch)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31))
    assert out.kpis.reinspecciones_notificacion_pendientes == 1


def test_pendientes_geolocalizacion_sigue_en_cero(app_ctx, monkeypatch) -> None:
    _patch_stock_query(
        monkeypatch,
        [
            _mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 5, 10)),
            _mk_ini(tipo="DENUNCIA", fecha=date(2026, 5, 11)),
        ],
    )
    _patch_map_point(monkeypatch)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31))
    assert out.kpis.pendientes_geolocalizacion == 0


def test_filtro_distrito_aplica_en_kpis(app_ctx, monkeypatch) -> None:
    inis = [
        _mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 5, 10)),
        _mk_ini(tipo="DENUNCIA", fecha=date(2026, 5, 11)),
        _mk_ini(tipo="REINSPECCION_OFICIO", fecha=date(2026, 5, 12)),
    ]
    _patch_stock_query(monkeypatch, inis)
    _patch_map_point(monkeypatch, distrito_id=99)
    out = build_indicadores_pendientes(date(2026, 5, 1), date(2026, 5, 31), distrito_id=99)
    assert out.kpis.relevamientos_pendientes == 1
    assert out.kpis.reinspecciones_oficio_pendientes == 1
    assert out.kpis.denuncias_pendientes == 1


def test_distritos_con_mas_pendientes_agrupa_por_tipo(app_ctx, monkeypatch) -> None:
    inis = [
        _mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 5, 10)),
        _mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 5, 11)),
        _mk_ini(tipo="REINSPECCION_OFICIO", fecha=date(2026, 5, 12)),
        _mk_ini(tipo="REINSPECCION_NOTIFICACION", fecha=date(2026, 5, 13)),
    ]
    _patch_stock_query(monkeypatch, inis)
    _patch_map_point(monkeypatch)

    out = build_indicadores_pendientes(date(2026, 1, 1), date(2026, 12, 31))
    assert len(out.distritos_con_mas_pendientes) == 1
    row = out.distritos_con_mas_pendientes[0]
    assert row.distrito_id == 99
    assert row.relevamientos == 2
    assert row.reinspecciones_oficio == 1
    assert row.reinspecciones_notificacion == 1
    assert row.denuncias == 0
    assert row.sin_geolocalizacion == 0
    assert row.total == 4


def test_iniciador_sin_geocode_no_cuenta(app_ctx, monkeypatch) -> None:
    ini = _mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 6, 1))
    _patch_stock_query(monkeypatch, [ini])
    monkeypatch.setattr(
        "app.domains.indicadores.services.indicadores_pendientes_queries._map_point_desde_iniciador_backlog",
        lambda *_a, **_k: None,
    )
    out = build_indicadores_pendientes(date(2026, 6, 1), date(2026, 6, 30))
    assert out.kpis.relevamientos_pendientes == 0


def test_inspector_id_no_filtra_pendientes(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [_mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 6, 1))])
    _patch_map_point(monkeypatch)
    sin_inspector = build_indicadores_pendientes(date(2026, 6, 1), date(2026, 6, 30))
    con_inspector = build_indicadores_pendientes(
        date(2026, 6, 1), date(2026, 6, 30), inspector_id=12345
    )
    assert _kpis_dict(sin_inspector.kpis) == _kpis_dict(con_inspector.kpis)


def test_aggregate_pendientes_stock_expone_metricas(app_ctx, monkeypatch) -> None:
    _patch_stock_query(monkeypatch, [_mk_ini(tipo="RELEVAMIENTO", fecha=date(2026, 1, 1))])
    _patch_map_point(monkeypatch)
    agg = aggregate_pendientes_stock()
    assert agg.scanned_count == 1
    assert agg.mapped_count == 1
