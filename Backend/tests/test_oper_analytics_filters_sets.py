"""
OPER-ANALYTICS-FILTERS.2 / 2.1 — Regresión por conjuntos de IDs.

Golden independiente (``fetch_filtered_operativo_ids``) vs servicio productivo del mapa
(``collect_mapa_operativo_universe_ids`` / ``list_mapa_operativo_cierres_geo_with_meta``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import db
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    collect_mapa_operativo_universe_ids,
    list_mapa_operativo_cierres_geo_with_meta,
)
from app.domains.indicadores.diagnostics.oper_analytics_golden import (
    fetch_filtered_operativo_ids,
    fetch_golden_dataset,
)
from app.domains.indicadores.services.indicadores_riesgo_service import build_indicadores_riesgo
from app.models import (
    Actuaciones,
    Contribuyente,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    Inspector,
    Motivo,
    OrdenTrabajo,
    Relevamiento,
    Rubro,
    RutaItem,
)
from tests.helpers.fixture_isolation import fecha_fixture_aislada, unique_ot_numero
from tests.indicadores_cierre_fixtures import vincular_cierre_realizado
from tests.oper_analytics_golden_fixtures import periodo_golden, seed_golden_world


def _iso_pair(desde, hasta) -> tuple[str, str]:
    return desde.isoformat(), hasta.isoformat()


def test_golden_fetch_no_delega_a_mapa_productivo() -> None:
    """FILTERS.2.1: el oracle golden no llama a collect_mapa_operativo_universe_ids."""
    src = Path(__file__).resolve().parents[1] / "app/domains/indicadores/diagnostics/oper_analytics_golden.py"
    text = src.read_text(encoding="utf-8")
    assert "collect_mapa_operativo_universe_ids" not in text
    assert "_base_intentos_query" in text


def _assert_mapa_golden_universe(
    desde,
    hasta,
    *,
    distrito_id: int | None = None,
    inspector_id: int | None = None,
    ejecucion: str = "TODOS",
    origen: str | None = None,
    motivo_no_realizado: str | None = None,
    rubro_id: int | None = None,
    tipo: str | None = None,
) -> None:
    """Oracle golden independiente == mapa productivo; features ⊆ golden."""
    d_iso, h_iso = _iso_pair(desde, hasta)
    golden = fetch_filtered_operativo_ids(
        desde,
        hasta,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
        ejecucion=ejecucion,
        origen=origen,
        motivo_no_realizado=motivo_no_realizado,
        rubro_id=rubro_id,
        tipo=tipo,
    )
    mapa_ids = collect_mapa_operativo_universe_ids(
        desde=d_iso,
        hasta=h_iso,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
        ejecucion=ejecucion,
        origen=origen,
        motivo_no_realizado=motivo_no_realizado,
        rubro_id=rubro_id,
        tipo=tipo,
    )
    assert golden == mapa_ids, f"golden-only {sorted(golden - mapa_ids)} mapa-only {sorted(mapa_ids - golden)}"

    mapa = list_mapa_operativo_cierres_geo_with_meta(
        desde=d_iso,
        hasta=h_iso,
        distrito_id=distrito_id,
        inspector_id=inspector_id,
        ejecucion=ejecucion,
        origen=origen,
        motivo_no_realizado=motivo_no_realizado,
        rubro_id=rubro_id,
        tipo=tipo,
    )
    assert mapa.meta["total_operativos"] == len(golden)
    feature_ids = {int(p["ruta_item_id"]) for p in mapa.points}
    assert feature_ids <= golden


def test_filters_sets_distrito_inspector(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        dist_row = next(r for r in rows if r.ruta_item_id == world.distrito_discrepante_item_id)
        inspector_id = ins_row.inspector_ids[0]
        distrito_id = dist_row.distrito_id_efectivo
        assert inspector_id is not None and distrito_id is not None

        _assert_mapa_golden_universe(
            desde,
            hasta,
            distrito_id=distrito_id,
            inspector_id=inspector_id,
        )
    finally:
        db.session.rollback()


def test_filters_sets_distrito_inspector_realizado(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        dist_row = next(r for r in rows if r.ruta_item_id == world.distrito_discrepante_item_id)

        _assert_mapa_golden_universe(
            desde,
            hasta,
            distrito_id=dist_row.distrito_id_efectivo,
            inspector_id=ins_row.inspector_ids[0],
            ejecucion="REALIZADO",
        )
    finally:
        db.session.rollback()


def test_filters_sets_distrito_inspector_no_realizado(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        dist_row = next(r for r in rows if r.ruta_item_id == world.distrito_discrepante_item_id)

        _assert_mapa_golden_universe(
            desde,
            hasta,
            distrito_id=dist_row.distrito_id_efectivo,
            inspector_id=ins_row.inspector_ids[0],
            ejecucion="NO_REALIZADO",
        )
    finally:
        db.session.rollback()


def test_filters_sets_origen_por_ejecucion(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)

        for ejecucion in ("TODOS", "REALIZADO", "NO_REALIZADO"):
            for origen in ("RELEVAMIENTO", "DENUNCIA", "REINSPECCION_NOTIFICACION", "OFICIO"):
                _assert_mapa_golden_universe(desde, hasta, ejecucion=ejecucion, origen=origen)
    finally:
        db.session.rollback()


def test_filters_sets_origen_motivo(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)

        _assert_mapa_golden_universe(
            desde,
            hasta,
            origen="RELEVAMIENTO",
            motivo_no_realizado="LOCAL_CERRADO",
        )
        _assert_mapa_golden_universe(
            desde,
            hasta,
            origen="REINSPECCION_NOTIFICACION",
            motivo_no_realizado="LOCAL_CERRADO",
        )
    finally:
        db.session.rollback()


def test_filters_sets_origen_distrito_motivo(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        rn = next(r for r in rows if r.ruta_item_id == world.rn_no_realizado_geo)

        _assert_mapa_golden_universe(
            desde,
            hasta,
            origen="REINSPECCION_NOTIFICACION",
            distrito_id=rn.distrito_id_efectivo,
            motivo_no_realizado="LOCAL_CERRADO",
        )
    finally:
        db.session.rollback()


def test_filters_sets_rubro_historico_relevamiento(app_ctx) -> None:
    """Rubro operativo del relevamiento prevalece sobre rubro actual del domicilio."""
    try:
        fecha = fecha_fixture_aislada(anio=2096)
        rub_hist = Rubro(nombre=f"RubHist_{unique_ot_numero()[:6]}")
        rub_actual = Rubro(nombre=f"RubAct_{unique_ot_numero()[:6]}")
        db.session.add_all([rub_hist, rub_actual])
        db.session.flush()

        c = Contribuyente(apellido="Rub", nombre="Hist", documento=unique_ot_numero())
        db.session.add(c)
        db.session.flush()
        dom = Domicilio(
            calle=f"RubHist_{unique_ot_numero()[:6]}",
            numero="50",
            rubro_id=rub_actual.id,
            contribuyente_id=c.id,
        )
        db.session.add(dom)
        db.session.flush()
        db.session.add(
            DomicilioGeocode(
                domicilio_id=dom.id,
                lat=-26.82,
                lng=-65.22,
                geo_status="OK",
            )
        )

        turno_ins = Inspector.query.first()
        rel = Relevamiento(
            fecha=fecha,
            mes=fecha.month,
            anio=fecha.year,
            inspector_id=turno_ins.id if turno_ins else 1,
            domicilio_id=dom.id,
            rubro_id=rub_hist.id,
        )
        db.session.add(rel)
        db.session.flush()

        act = Actuaciones(
            fecha=fecha,
            mes=fecha.month,
            anio=fecha.year,
            tipo="INSPECCION",
            domicilio_id=dom.id,
            orden_trabajo_id=None,
        )
        ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
        db.session.add(ot)
        db.session.flush()
        act.orden_trabajo_id = ot.id
        db.session.add(act)
        db.session.flush()

        item = vincular_cierre_realizado(act, fecha, tipo_iniciador="RELEVAMIENTO", fecha_ruta=fecha)
        ini = item.iniciador_ruta
        assert ini is not None
        ini.relevamiento_id = rel.id
        db.session.flush()

        ids_hist = fetch_filtered_operativo_ids(
            fecha, fecha, rubro_id=rub_hist.id, ejecucion="REALIZADO"
        )
        ids_actual = fetch_filtered_operativo_ids(
            fecha, fecha, rubro_id=rub_actual.id, ejecucion="REALIZADO"
        )
        assert item.id in ids_hist
        assert item.id not in ids_actual
    finally:
        db.session.rollback()


def test_rn_origen_no_usa_notificacion_en_relevamiento(app_ctx) -> None:
    """Relevamiento con notificación labrada no aparece al filtrar RN (FIX.8)."""
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)

        rows = fetch_golden_dataset(desde, hasta)
        rel_row = next(r for r in rows if r.ruta_item_id == world.relevamiento_realizado_geo)
        dom_id = rel_row.domicilio_id_efectivo
        assert dom_id is not None

        ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=desde.year, mes=desde.month)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(
            fecha=desde,
            mes=desde.month,
            anio=desde.year,
            tipo="INSPECCION",
            domicilio_id=dom_id,
            orden_trabajo_id=ot.id,
        )
        db.session.add(act)
        db.session.flush()
        motivo = Motivo.query.first()
        if motivo is None:
            motivo = Motivo(nombre=f"MotRN_{unique_ot_numero()[:6]}")
            db.session.add(motivo)
            db.session.flush()
        attach_notificacion(act, {"acta_num": unique_ot_numero(), "motivos": [motivo.nombre]})
        item_rel_notif = vincular_cierre_realizado(
            act, desde, tipo_iniciador="RELEVAMIENTO", fecha_ruta=desde
        )
        db.session.flush()

        rn_ids = fetch_filtered_operativo_ids(
            desde, hasta, origen="REINSPECCION_NOTIFICACION", ejecucion="TODOS"
        )
        assert item_rel_notif.id not in rn_ids
        assert world.rn_no_realizado_geo in rn_ids
    finally:
        db.session.rollback()


def test_distrito_efectivo_act_gana_sobre_ini(app_ctx) -> None:
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        row = next(r for r in rows if r.ruta_item_id == world.distrito_discrepante_item_id)
        assert row.distrito_id_actuacion != row.distrito_id_iniciador

        ids_act = fetch_filtered_operativo_ids(
            desde, hasta, distrito_id=row.distrito_id_actuacion
        )
        ids_ini = fetch_filtered_operativo_ids(
            desde, hasta, distrito_id=row.distrito_id_iniciador
        )
        assert world.distrito_discrepante_item_id in ids_act
        assert world.distrito_discrepante_item_id not in ids_ini
    finally:
        db.session.rollback()


def test_inspector_grupo_y_actuacion_un_solo_intento(app_ctx) -> None:
    """Tres inspectores en actuaciones_inspector: un solo RutaItem en el universo filtrado."""
    try:
        world = seed_golden_world()
        db.session.flush()
        desde, hasta = periodo_golden(world.fecha_ruta)
        rows = fetch_golden_dataset(desde, hasta)
        ins_row = next(r for r in rows if r.ruta_item_id == world.tres_inspectores_item_id)
        assert ins_row.inspector_cantidad == 3

        for inspector_id in ins_row.inspector_ids:
            ids = fetch_filtered_operativo_ids(desde, hasta, inspector_id=inspector_id)
            assert world.tres_inspectores_item_id in ids
    finally:
        db.session.rollback()


def test_decomiso_kg_domicilio_solo_en_iniciador(app_ctx) -> None:
    """Kg por rubro y filtro distrito usan domicilio efectivo (iniciador si act es null)."""
    try:
        fecha = fecha_fixture_aislada(anio=2095)
        distritos = Distrito.query.limit(3).all()
        assert len(distritos) >= 1
        dist = distritos[2] if len(distritos) > 2 else distritos[0]

        rub = Rubro(nombre=f"RubDecoIni_{unique_ot_numero()[:6]}")
        db.session.add(rub)
        db.session.flush()
        c = Contribuyente(apellido="Dec", nombre="Ini", documento=unique_ot_numero())
        db.session.add(c)
        db.session.flush()
        dom = Domicilio(
            calle=f"DecIni_{unique_ot_numero()[:6]}",
            numero="7",
            rubro_id=rub.id,
            contribuyente_id=c.id,
            distrito_id=dist.id,
        )
        db.session.add(dom)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=fecha.year, mes=fecha.month)
        db.session.add(ot)
        db.session.flush()
        act = Actuaciones(
            fecha=fecha,
            mes=fecha.month,
            anio=fecha.year,
            tipo="INSPECCION",
            domicilio_id=None,
            orden_trabajo_id=ot.id,
        )
        db.session.add(act)
        db.session.flush()
        attach_decomiso(act, {"acta_num": unique_ot_numero(), "kilos_total": 33.3})
        vincular_cierre_realizado(
            act, fecha, tipo_iniciador="RELEVAMIENTO", fecha_ruta=fecha, ini_domicilio_id=dom.id
        )
        db.session.flush()

        out = build_indicadores_riesgo(fecha, fecha, distrito_id=dist.id)
        by_rubro = {r.rubro: r.kg for r in out.decomiso_kg_por_rubro}
        assert abs(by_rubro.get(rub.nombre, 0) - 33.3) < 0.01

        out_all = build_indicadores_riesgo(fecha, fecha)
        assert abs(dict((r.rubro, r.kg) for r in out_all.decomiso_kg_por_rubro).get(rub.nombre, 0) - 33.3) < 0.01
    finally:
        db.session.rollback()
