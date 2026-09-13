"""
OPER-ANALYTICS.3 — Regresión mapa operativo unificado vs golden fixtures.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.database import db
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    list_mapa_operativo_cierres_geo_with_meta,
)
from app.domains.indicadores.diagnostics.oper_analytics_golden import (
    compare_mapa,
    fetch_golden_dataset,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    aggregate_contraproducencia_buckets_from_visita_rows,
    fetch_no_realizadas_visita_rows,
)
from app.domains.indicadores.utils.contraproducencia_indicador_buckets import (
    classify_motivo_no_realizado_indicador,
)
from tests.indicadores_cierre_fixtures import vincular_cierre_no_realizado, vincular_cierre_realizado
from tests.oper_analytics_golden_fixtures import periodo_golden, seed_golden_world
from tests.helpers.fixture_isolation import fecha_fixture_aislada, unique_ot_numero


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_mapa_fecha_ruta_no_ejecutado_at(app_ctx) -> None:
    """Ruta en enero con ejecutado_at en febrero: aparece filtrando enero."""
    from app.models import Actuaciones, Contribuyente, Domicilio, DomicilioGeocode, Rubro

    fecha_ruta = date(2097, 1, 15)
    fecha_ejec = fecha_ruta + timedelta(days=17)
    rub = Rubro.query.first()
    assert rub is not None
    c = Contribuyente(apellido="F", nombre="Mapa", documento=unique_ot_numero())
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=f"MapaFecha_{unique_ot_numero()}", numero="1", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    db.session.add(
        DomicilioGeocode(
            domicilio_id=dom.id,
            lat=-34.6,
            lng=-58.4,
            geo_status="OK",
        )
    )
    from app.models import OrdenTrabajo

    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha_ruta.year, mes=fecha_ruta.month)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_ruta,
        mes=fecha_ruta.month,
        anio=fecha_ruta.year,
        tipo="INSPECCION",
        domicilio_id=dom.id,
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()
    vincular_cierre_realizado(
        act,
        fecha_ruta,
        tipo_iniciador="RELEVAMIENTO",
        fecha_ruta=fecha_ruta,
        fecha_ejecutado=datetime(fecha_ejec.year, fecha_ejec.month, fecha_ejec.day, 10, 0),
    )
    db.session.flush()

    enero = list_mapa_operativo_cierres_geo_with_meta(
        desde=fecha_ruta.isoformat(),
        hasta=date(fecha_ruta.year, fecha_ruta.month, 28).isoformat(),
        ejecucion="REALIZADO",
    )
    febrero = list_mapa_operativo_cierres_geo_with_meta(
        desde=fecha_ejec.isoformat(),
        hasta=fecha_ejec.isoformat(),
        ejecucion="REALIZADO",
    )
    assert enero.meta["realizados"] >= 1
    assert febrero.meta["realizados"] == 0


def test_mapa_no_realizado_filtros_ejecucion(app_ctx) -> None:
    world = seed_golden_world()
    db.session.flush()
    desde, hasta = periodo_golden(world.fecha_ruta)

    todos = list_mapa_operativo_cierres_geo_with_meta(
        desde=desde.isoformat(), hasta=hasta.isoformat(), ejecucion="TODOS"
    )
    solo_real = list_mapa_operativo_cierres_geo_with_meta(
        desde=desde.isoformat(), hasta=hasta.isoformat(), ejecucion="REALIZADO"
    )
    solo_nr = list_mapa_operativo_cierres_geo_with_meta(
        desde=desde.isoformat(), hasta=hasta.isoformat(), ejecucion="NO_REALIZADO"
    )
    nr_ids = {p["ruta_item_id"] for p in solo_nr.points}
    assert world.rn_no_realizado_geo in nr_ids
    assert world.rn_no_realizado_geo not in {p["ruta_item_id"] for p in solo_real.points}
    assert world.rn_no_realizado_geo in {p["ruta_item_id"] for p in todos.points} or todos.meta[
        "no_realizados"
    ] >= 1

    filtrado = list_mapa_operativo_cierres_geo_with_meta(
        desde=desde.isoformat(),
        hasta=hasta.isoformat(),
        ejecucion="NO_REALIZADO",
        motivo_no_realizado="LOCAL_CERRADO",
    )
    assert world.rn_no_realizado_geo in {p["ruta_item_id"] for p in filtrado.points}


def test_no_realizados_total_buckets_reconciliados(app_ctx) -> None:
    world = seed_golden_world()
    db.session.flush()
    desde, hasta = periodo_golden(world.fecha_ruta)
    rows = fetch_no_realizadas_visita_rows(desde, hasta)
    fixture_nr = [r for r in fetch_golden_dataset(desde, hasta) if r.estado_ejecucion == "NO_REALIZADO"]
    assert len(rows) == len(fixture_nr)
    buckets = aggregate_contraproducencia_buckets_from_visita_rows(rows)
    assert sum(buckets.values()) == len(rows)
    for row in rows:
        assert classify_motivo_no_realizado_indicador(row.motivo_no_realizado, row.contraproducencia)


def test_golden_mapa_alineado_tras_unificacion(app_ctx) -> None:
    world = seed_golden_world()
    db.session.flush()
    desde, hasta = periodo_golden(world.fecha_ruta)
    rows = fetch_golden_dataset(desde, hasta)
    fixture_rows = [r for r in rows if r.ruta_item_id in world.expected_universe_ids]
    mapa = compare_mapa(desde, hasta, fixture_rows)
    esperado = {
        r.ruta_item_id
        for r in fixture_rows
        if r.estado_ejecucion == "REALIZADO"
        and r.dibujable_en_mapa
        and desde <= r.fecha_ruta <= hasta
    }
    mapa_en_fixture = set(mapa.mapa_ids) & set(world.expected_universe_ids)
    assert esperado == mapa_en_fixture
