"""Historial notificación: una fila canónica por notificacion_id (sin duplicar REINSPECCION)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_reinspeccion_comprobacion_por_actuacion_id,
    dedupe_actuaciones_canonicas_por_notificacion,
    get_pendientes_expediente,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.models import Actuaciones, Comprobacion, Notificacion, OrdenTrabajo


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _filters_notificacion() -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {"desde": "2026-01-01", "hasta": "2026-12-31", "source_type": "notificacion"}
    )


def _mk_origen_y_reinspeccion() -> tuple[Actuaciones, Actuaciones, Notificacion, str]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
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
        tipo="INSPECCION",
    )
    db.session.add(act_origen)
    db.session.flush()

    ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot2)
    db.session.flush()
    comp_rein = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="rein")
    db.session.add(comp_rein)
    db.session.flush()
    rein_num = comp_rein.numero_acta
    act_rein = Actuaciones(
        fecha=date(2026, 4, 1),
        mes=4,
        anio=2026,
        orden_trabajo_id=ot2.id,
        notificacion_id=noti.id,
        comprobacion_id=comp_rein.id,
        tipo="REINSPECCION",
    )
    db.session.add(act_rein)
    db.session.flush()
    return act_origen, act_rein, noti, rein_num


def test_dedupe_prefiere_inspeccion_origen(app_ctx) -> None:
    try:
        act_origen, act_rein, noti, _rein_num = _mk_origen_y_reinspeccion()
        acts = dedupe_actuaciones_canonicas_por_notificacion([act_rein, act_origen])
        assert len(acts) == 1
        assert acts[0].id == act_origen.id
        assert acts[0].notificacion_id == noti.id
    finally:
        db.session.rollback()


def test_get_pendientes_expediente_notificacion_no_duplica_por_reinspeccion(app_ctx) -> None:
    try:
        act_origen, act_rein, noti, _rein_num = _mk_origen_y_reinspeccion()
        acts = get_pendientes_expediente(_filters_notificacion())
        noti_ids = [a.notificacion_id for a in acts if a.notificacion_id == noti.id]
        assert noti_ids.count(noti.id) == 1
        canonical = next(a for a in acts if a.notificacion_id == noti.id)
        assert canonical.id == act_origen.id
        assert act_rein.id not in [a.id for a in acts if a.notificacion_id == noti.id]
    finally:
        db.session.rollback()


def test_historial_fila_canonica_incluye_comprobacion_reinspeccion(app_ctx) -> None:
    try:
        act_origen, _act_rein, noti, rein_num = _mk_origen_y_reinspeccion()
        acts = dedupe_actuaciones_canonicas_por_notificacion([act_origen])
        plazos, venc, prorroga_dias = build_notificacion_expediente_bandeja_metrics(acts)
        rein_map = build_reinspeccion_comprobacion_por_actuacion_id(acts)
        counts = build_counts_by_eo_from_actuaciones(acts)
        row = actuacion_to_pendiente_expediente_row(
            acts[0],
            plazos_por_notificacion=plazos,
            fecha_vencimiento_por_notificacion=venc,
            prorroga_dias_por_notificacion=prorroga_dias,
            counts_by_eo=counts,
            reinspeccion_comprobacion_por_actuacion_id=rein_map,
            expediente_list_channel="notificacion",
        )
        assert row["notificacion_id"] == noti.id
        assert row.get("comprobacion_posterior_acta_num") == rein_num
    finally:
        db.session.rollback()
