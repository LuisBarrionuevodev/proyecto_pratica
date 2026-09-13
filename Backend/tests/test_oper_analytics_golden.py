"""
OPER-ANALYTICS.2 — Golden dataset y baseline operativo (fixtures controlados).
"""

from __future__ import annotations

import pytest

from app.database import db
from app.domains.indicadores.diagnostics.oper_analytics_golden import (
    compare_dashboard,
    compare_mapa,
    compute_baseline_metrics,
    fetch_golden_dataset,
)
from tests.oper_analytics_golden_fixtures import periodo_golden, seed_golden_world


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_golden_universo_canonico_y_exclusiones(app_ctx) -> None:
    """Solo intentos FINALIZADOS con ejecución REALIZADO/NO_REALIZADO entran al universo."""
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        fixture_rows = [r for r in rows if r.ruta_item_id in world.expected_universe_ids]
        ids = {r.ruta_item_id for r in fixture_rows}

        for expected_id in world.expected_universe_ids:
            assert expected_id in ids

        assert world.documental_actuacion_id not in {r.actuacion_id for r in fixture_rows}
        assert world.planning_item_id not in ids
        assert world.legacy_no_realizado_item_id not in ids

        assert len(fixture_rows) == len(world.expected_universe_ids)
        assert all(r.pertenece_universo_operativo for r in fixture_rows)
        assert all(r.orden_trabajo_id for r in fixture_rows)
    finally:
        db.session.rollback()


def test_golden_ejecucion_y_geo(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        by_id = {r.ruta_item_id: r for r in rows}

        rel = by_id[world.relevamiento_realizado_geo]
        assert rel.estado_ejecucion == "REALIZADO"
        assert rel.tiene_geocode_ok is True
        assert rel.dibujable_en_mapa is True

        den = by_id[world.denuncia_realizado_sin_geo]
        assert den.estado_ejecucion == "REALIZADO"
        assert den.tiene_geocode_ok is False
        assert den.dibujable_en_mapa is False

        rn = by_id[world.rn_no_realizado_geo]
        assert rn.estado_ejecucion == "NO_REALIZADO"
        assert rn.tiene_geocode_ok is True
        assert rn.dibujable_en_mapa is True

        assert world.reintento_1 in by_id and world.reintento_2 in by_id
        assert by_id[world.reintento_1].domicilio_id_efectivo == by_id[world.reintento_2].domicilio_id_efectivo
    finally:
        db.session.rollback()


def test_golden_tres_inspectores_cuenta_un_intento(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        assert ins_row.inspector_cantidad == 3
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        assert ins_row.kg_decomisados >= 12.5
        metrics = compute_baseline_metrics(
            [r for r in rows if r.ruta_item_id in world.expected_universe_ids]
        )
        assert metrics.total_realizados >= 1
        assert metrics.kg_realizados >= 12.5
    finally:
        db.session.rollback()


def test_golden_actas_suma_coherente(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        metrics = compute_baseline_metrics(rows)
        assert metrics.total_actas_labradas == (
            metrics.actas_inspeccion
            + metrics.actas_notificacion
            + metrics.actas_comprobacion
            + metrics.actas_clausura
            + metrics.actas_decomiso
        )
        vi = next(r for r in rows if r.ruta_item_id == world.verificar_con_inspeccion)
        assert vi.acta_inspeccion is True
        assert vi.cantidad_actas_labradas >= 1
    finally:
        db.session.rollback()


def test_golden_verificar_informar_desglose(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        metrics = compute_baseline_metrics(fetch_golden_dataset(desde, hasta))
        assert metrics.verificar_informar.get("C_realizado_con_inspeccion", 0) >= 1
        assert metrics.verificar_informar.get("B_realizado_sin_inspeccion", 0) >= 1
    finally:
        db.session.rollback()


def test_golden_discrepancias_fecha_y_distrito(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        by_id = {r.ruta_item_id: r for r in rows}

        fecha_row = by_id[world.fecha_discrepante_item_id]
        assert fecha_row.difiere_fecha_ruta_ejecucion is True

        dist_row = by_id[world.distrito_discrepante_item_id]
        assert dist_row.domicilios_difieren is True
        assert dist_row.distrito_discrepante is True
        assert dist_row.distrito_id_actuacion != dist_row.distrito_id_iniciador
    finally:
        db.session.rollback()


def test_golden_no_realizados_dibujables(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        metrics = compute_baseline_metrics(fetch_golden_dataset(desde, hasta))
        assert world.rn_no_realizado_geo in metrics.no_realizados_dibujables
        assert metrics.no_realizados_con_geo >= 2
    finally:
        db.session.rollback()


def test_golden_comparacion_dashboard_y_mapa(app_ctx) -> None:
    """En día aislado, baseline de fixtures y dashboard deben coincidir."""
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        fixture_rows = [r for r in rows if r.ruta_item_id in world.expected_universe_ids]
        dashboard = compare_dashboard(desde, hasta, fixture_rows)

        realizadas = next(r for r in dashboard if r.kpi == "actuaciones_realizadas")
        no_real = next(r for r in dashboard if r.kpi == "no_realizadas")
        assert realizadas.diferencia == 0
        assert no_real.diferencia == 0

        mapa = compare_mapa(desde, hasta, fixture_rows)
        # Mapa productivo: REALIZADO + geo en domicilio actuación + ventana coalesce(ejecutado_at, fecha_ruta).
        fixture_en_mapa_esperado = {
            r.ruta_item_id
            for r in fixture_rows
            if r.estado_ejecucion == "REALIZADO"
            and r.dibujable_en_mapa
            and desde <= r.fecha_ruta <= hasta
        }
        mapa_en_fixture = set(mapa.mapa_ids) & set(world.expected_universe_ids)
        assert fixture_en_mapa_esperado == mapa_en_fixture

        den_row = next(r for r in fixture_rows if r.ruta_item_id == world.denuncia_realizado_sin_geo)
        assert den_row.tiene_geocode_ok is False
        assert den_row.dibujable_en_mapa is False  # sin geo en domicilio efectivo
        assert world.denuncia_realizado_sin_geo not in mapa.mapa_ids

        assert world.fecha_discrepante_item_id in fixture_en_mapa_esperado
    finally:
        db.session.rollback()


def test_golden_filtro_distrito_modos(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows_all = fetch_golden_dataset(desde, hasta)
        dist_row = next(r for r in rows_all if r.ruta_item_id == world.distrito_discrepante_item_id)
        assert dist_row.distrito_id_efectivo is not None
        assert dist_row.distrito_id_actuacion is not None

        eff_count = len(
            fetch_golden_dataset(
                desde,
                hasta,
                distrito_id=dist_row.distrito_id_efectivo,
                distrito_modo="efectivo",
            )
        )
        act_count = len(
            fetch_golden_dataset(
                desde,
                hasta,
                distrito_id=dist_row.distrito_id_actuacion,
                distrito_modo="actuacion",
            )
        )
        ini_count = len(
            fetch_golden_dataset(
                desde,
                hasta,
                distrito_id=dist_row.distrito_id_iniciador,
                distrito_modo="iniciador",
            )
        )
        assert eff_count >= 1
        assert act_count >= 1
        assert ini_count >= 1
        if dist_row.distrito_id_actuacion != dist_row.distrito_id_iniciador:
            assert act_count != ini_count
    finally:
        db.session.rollback()
