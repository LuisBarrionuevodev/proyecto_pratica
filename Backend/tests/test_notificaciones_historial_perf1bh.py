"""
GESTIÓN-PERF.1-BH — Historial notificaciones: filtros SQL + paginación server-side.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.pendientes_service import (
    dedupe_actuaciones_canonicas_por_notificacion,
    get_historial_notificacion_expediente_paginado,
    get_historial_notificacion_legacy_ids,
    get_pendientes_expediente,
    pick_canonical_actuacion_ids_from_tuples,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Motivo, Notificacion, OrdenTrabajo


def _unique_num() -> str:
    return uuid4().hex[:6].upper()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app({"TESTING": True})
    with app.app_context():
        yield app
        db.session.rollback()


def _base_filters(**extra) -> dict:
    return {
        "desde": "2026-01-01",
        "hasta": "2026-12-31",
        "source_type": "notificacion",
        **extra,
    }


def _filters_historial(**extra) -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {**_base_filters(), "page": 1, "page_size": 10, **extra}
    )


def _mk_actuacion_solo_notificacion(
    *,
    calle: str = "CalleDefault",
    contrib_apellido: str = "ApellidoDefault",
    numero_acta: str | None = None,
    motivo_nombre: str | None = None,
) -> tuple[Actuaciones, Notificacion, int | None]:
    contrib = Contribuyente(apellido=contrib_apellido, nombre="Nombre", documento=_unique_num())
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(calle=calle, numero="100", contribuyente_id=contrib.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=numero_acta or _unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    motivo_id: int | None = None
    if motivo_nombre:
        mot = Motivo(nombre=motivo_nombre)
        db.session.add(mot)
        db.session.flush()
        noti.motivos.append(mot)
        motivo_id = int(mot.id)
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti, motivo_id


def _mk_origen_y_reinspeccion_distintas_calles() -> tuple[Actuaciones, Actuaciones, Notificacion]:
    """INSPECCION canónica (Maipú) + REINSPECCION histórica (San Martín), misma notificación."""
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))

    dom_canon = Domicilio(calle="MaipuBHTestCanonica", numero="10")
    dom_hist = Domicilio(calle="SanMartinBHTestHist", numero="20")
    db.session.add_all([dom_canon, dom_hist])
    db.session.flush()

    comp_origen = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="m")
    db.session.add(comp_origen)
    db.session.flush()
    act_origen = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        comprobacion_id=comp_origen.id,
        domicilio_id=dom_canon.id,
        tipo="INSPECCION",
    )
    db.session.add(act_origen)
    db.session.flush()

    ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=4)
    db.session.add(ot2)
    db.session.flush()
    comp_rein = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=4, motivo="rein")
    db.session.add(comp_rein)
    db.session.flush()
    act_rein = Actuaciones(
        fecha=date(2026, 4, 1),
        mes=4,
        anio=2026,
        orden_trabajo_id=ot2.id,
        notificacion_id=noti.id,
        comprobacion_id=comp_rein.id,
        domicilio_id=dom_hist.id,
        tipo="REINSPECCION",
    )
    db.session.add(act_rein)
    db.session.flush()
    return act_origen, act_rein, noti


def _sql_historial_all_ids(filters: ActuacionesPendientesFilters, page_size: int = 10) -> tuple[list[int], int]:
    all_ids: list[int] = []
    page = 1
    total = 0
    while True:
        f = ActuacionesPendientesFilters.model_validate(
            {
                **filters.model_dump(exclude_none=True),
                "page": page,
                "page_size": page_size,
            }
        )
        acts, total = get_historial_notificacion_expediente_paginado(f)
        all_ids.extend([int(a.id) for a in acts])
        if len(acts) < page_size:
            break
        page += 1
    return all_ids, total


class TestPerf1BhCanonicalidad:
    def test_pick_canonical_ids_coincide_con_dedupe(self, app_ctx) -> None:
        try:
            act_origen, act_rein, noti = _mk_origen_y_reinspeccion_distintas_calles()
            tuples = [
                (int(act_rein.id), int(noti.id), act_rein.tipo),
                (int(act_origen.id), int(noti.id), act_origen.tipo),
            ]
            sql_ids = pick_canonical_actuacion_ids_from_tuples(tuples)
            dedupe_ids = [int(a.id) for a in dedupe_actuaciones_canonicas_por_notificacion([act_rein, act_origen])]
            assert sql_ids == dedupe_ids
            assert sql_ids == [int(act_origen.id)]
        finally:
            db.session.rollback()

    def test_bh_calle_no_canonica_no_filtra_antes_de_dedupe(self, app_ctx) -> None:
        """Calle en actuación histórica no debe mostrar fila si la canónica no coincide."""
        try:
            act_origen, _act_rein, noti = _mk_origen_y_reinspeccion_distintas_calles()
            fl = _filters_historial(calle_q="SanMartinBHTestHist", omitir_rango_fecha=True)
            legacy = get_historial_notificacion_legacy_ids(fl)
            sql_page, total = get_historial_notificacion_expediente_paginado(fl)
            assert int(act_origen.id) not in legacy
            assert total == 0
            assert sql_page == []
            fl_ok = _filters_historial(calle_q="MaipuBHTestCanonica", omitir_rango_fecha=True)
            assert int(act_origen.id) in get_historial_notificacion_legacy_ids(fl_ok)
            acts_ok, total_ok = get_historial_notificacion_expediente_paginado(fl_ok)
            assert total_ok == 1
            assert [int(a.id) for a in acts_ok] == [int(act_origen.id)]
        finally:
            db.session.rollback()


class TestPerf1BhFiltrosLegacyVsSql:
    def test_bh_ids_legacy_igual_sql_sin_filtro_documental(self, app_ctx) -> None:
        try:
            act, _noti, _ = _mk_actuacion_solo_notificacion()
            fl = _filters_historial()
            legacy = get_historial_notificacion_legacy_ids(fl)
            sql_all, total = _sql_historial_all_ids(fl)
            assert int(act.id) in legacy
            assert sql_all == legacy
            assert total == len(legacy)
        finally:
            db.session.rollback()

    def test_bh_filtros_documentales_legacy_igual_sql(self, app_ctx) -> None:
        try:
            act, noti, motivo_id = _mk_actuacion_solo_notificacion(
                calle="CalleDocFilterXyz",
                contrib_apellido="DocFilterApellido",
                numero_acta="777666",
                motivo_nombre="InfraccionDocFilterTipo",
            )
            assert motivo_id is not None
            base = _base_filters()
            cases = [
                {"contribuyente_q": "DocFilterApellido"},
                {"calle_q": "DocFilterXyz"},
                {"numero_notificacion": "776"},
                {"motivo_id": motivo_id},
                {"contribuyente_q": "DocFilterApellido", "calle_q": "DocFilterXyz"},
            ]
            for extra in cases:
                fl = _filters_historial(**extra)
                legacy = get_historial_notificacion_legacy_ids(fl)
                sql_all, total = _sql_historial_all_ids(fl)
                assert int(act.id) in legacy
                assert sql_all == legacy
                assert total == len(legacy)
            fl_miss = _filters_historial(contribuyente_q="NOEXISTE999")
            assert int(act.id) not in get_historial_notificacion_legacy_ids(fl_miss)
            assert int(act.id) not in _sql_historial_all_ids(fl_miss)[0]
        finally:
            db.session.rollback()


class TestPerf1BhMotivoId:
    def test_bh_motivo_id_exacto_no_texto(self, app_ctx) -> None:
        try:
            act_a, _noti_a, mot_a = _mk_actuacion_solo_notificacion(
                motivo_nombre="MotivoBHExactoA",
                contrib_apellido="MotivoBHExactoA",
            )
            act_b, _noti_b, mot_b = _mk_actuacion_solo_notificacion(
                motivo_nombre="MotivoBHExactoB",
                contrib_apellido="MotivoBHExactoB",
            )
            assert mot_a is not None and mot_b is not None
            fl = _filters_historial(motivo_id=mot_a, omitir_rango_fecha=True)
            sql_ids, total = _sql_historial_all_ids(fl)
            legacy_ids = get_historial_notificacion_legacy_ids(fl)
            assert int(act_a.id) in sql_ids
            assert int(act_b.id) not in sql_ids
            assert sql_ids == legacy_ids
            assert total == len(legacy_ids)
        finally:
            db.session.rollback()

    def test_bh_motivo_id_y_calle_and(self, app_ctx) -> None:
        try:
            act, _noti, mot_id = _mk_actuacion_solo_notificacion(
                calle="CalleMotivoBHAnd",
                motivo_nombre="MotivoBHAnd",
                contrib_apellido="MotivoBHAnd",
            )
            assert mot_id is not None
            fl_ok = _filters_historial(
                motivo_id=mot_id,
                calle_q="CalleMotivoBHAnd",
                omitir_rango_fecha=True,
            )
            fl_miss = _filters_historial(
                motivo_id=mot_id,
                calle_q="OtraCalleBHAnd",
                omitir_rango_fecha=True,
            )
            assert int(act.id) in get_historial_notificacion_legacy_ids(fl_ok)
            assert int(act.id) not in get_historial_notificacion_legacy_ids(fl_miss)
        finally:
            db.session.rollback()

    def test_bh_motivo_id_vacio_sin_filtro(self, app_ctx) -> None:
        try:
            act, _noti, _ = _mk_actuacion_solo_notificacion(contrib_apellido="MotivoBHVacio")
            fl = _filters_historial(omitir_rango_fecha=True)
            assert int(act.id) in get_historial_notificacion_legacy_ids(fl)
            fl_none = _filters_historial(motivo_id=None, omitir_rango_fecha=True)
            assert int(act.id) in get_historial_notificacion_legacy_ids(fl_none)
        finally:
            db.session.rollback()


class TestPerf1BhPaginacion:
    def test_bh_paginacion_25_filas_page_size_10(self, app_ctx) -> None:
        try:
            created_ids: list[int] = []
            for i in range(25):
                act, _, _ = _mk_actuacion_solo_notificacion(calle=f"PagBH{i}", contrib_apellido=f"PagBH{i}")
                created_ids.append(int(act.id))
            fl = _filters_historial(contribuyente_q="PagBH", omitir_rango_fecha=True)
            legacy = get_historial_notificacion_legacy_ids(fl)
            assert len(legacy) >= 25

            p1, t1 = get_historial_notificacion_expediente_paginado(
                ActuacionesPendientesFilters.model_validate({**fl.model_dump(exclude_none=True), "page": 1})
            )
            p2, _ = get_historial_notificacion_expediente_paginado(
                ActuacionesPendientesFilters.model_validate({**fl.model_dump(exclude_none=True), "page": 2})
            )
            p3, total = get_historial_notificacion_expediente_paginado(
                ActuacionesPendientesFilters.model_validate({**fl.model_dump(exclude_none=True), "page": 3})
            )
            assert len(p1) == 10
            assert len(p2) == 10
            assert len(p3) == 5
            assert total >= 25

            page_ids = [int(a.id) for a in p1] + [int(a.id) for a in p2] + [int(a.id) for a in p3]
            assert len(page_ids) == len(set(page_ids))
            sql_all, total_all = _sql_historial_all_ids(fl)
            assert len(sql_all) == len(set(sql_all))
            assert sorted(sql_all) == sorted(legacy)
            assert total_all == total
        finally:
            db.session.rollback()

    def test_bh_presenter_solo_pagina_actual(self, app_ctx) -> None:
        try:
            for i in range(15):
                _mk_actuacion_solo_notificacion(calle=f"PresBH{i}", contrib_apellido=f"PresBH{i}")
            fl = _filters_historial(contribuyente_q="PresBH", omitir_rango_fecha=True)
            acts, total = get_historial_notificacion_expediente_paginado(fl)
            assert len(acts) == 10
            assert total >= 15
        finally:
            db.session.rollback()


class TestPerf1BhOperativaIntacta:
    def test_bh_page_size_no_afecta_en_plazo(self, app_ctx) -> None:
        f_base = ActuacionesPendientesFilters.model_validate(
            {
                "source_type": "notificacion",
                "omitir_rango_fecha": True,
                "plazo_slice": "en_plazo",
            }
        )
        f_pag = ActuacionesPendientesFilters.model_validate(
            {
                "source_type": "notificacion",
                "omitir_rango_fecha": True,
                "plazo_slice": "en_plazo",
                "page": 1,
                "page_size": 10,
            }
        )
        a = get_pendientes_expediente(f_base)
        b = get_pendientes_expediente(f_pag)
        assert [int(x.id) for x in a] == [int(x.id) for x in b]
