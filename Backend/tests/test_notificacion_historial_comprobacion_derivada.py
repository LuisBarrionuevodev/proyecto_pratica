"""Historial notificación: comprobación posterior = reinspección, no origen."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_reinspeccion_comprobacion_por_actuacion_id,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Notificacion, OrdenTrabajo


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _row_for_act(act: Actuaciones) -> dict:
    acts = [act]
    plazos, venc = build_notificacion_expediente_bandeja_metrics(acts)
    rein = build_reinspeccion_comprobacion_por_actuacion_id(acts)
    counts = build_counts_by_eo_from_actuaciones(acts)
    return actuacion_to_pendiente_expediente_row(
        act,
        plazos_por_notificacion=plazos,
        fecha_vencimiento_por_notificacion=venc,
        counts_by_eo=counts,
        reinspeccion_comprobacion_por_actuacion_id=rein,
        expediente_list_channel="notificacion",
    )


def test_historial_muestra_comprobacion_reinspeccion(app_ctx) -> None:
    try:
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
        act = Actuaciones(
            fecha=date(2026, 3, 1),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            notificacion_id=noti.id,
            comprobacion_id=comp_origen.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot2)
        db.session.flush()
        comp_rein = Comprobacion(numero_acta="REIN99", anio=2026, mes=3, motivo="rein")
        db.session.add(comp_rein)
        db.session.flush()
        act_rein = Actuaciones(
            fecha=date(2026, 4, 10),
            mes=4,
            anio=2026,
            orden_trabajo_id=ot2.id,
            notificacion_id=noti.id,
            comprobacion_id=comp_rein.id,
            tipo="REINSPECCION",
        )
        db.session.add(act_rein)
        db.session.flush()

        row = _row_for_act(act)
        assert row["comprobacion_posterior_acta_num"] == "REIN99"
        assert row["comprobacion_posterior_fecha"] == "2026-04-10"
    finally:
        db.session.rollback()


def test_historial_sin_comprobacion_reinspeccion_no_inventa(app_ctx) -> None:
    try:
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()
        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(noti)
        db.session.flush()
        inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
        act = Actuaciones(
            fecha=date(2026, 3, 1),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            notificacion_id=noti.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot2)
        db.session.flush()
        act_rein = Actuaciones(
            fecha=date(2026, 4, 10),
            mes=4,
            anio=2026,
            orden_trabajo_id=ot2.id,
            notificacion_id=noti.id,
            tipo="REINSPECCION",
        )
        db.session.add(act_rein)
        db.session.flush()

        row = _row_for_act(act)
        assert row["comprobacion_posterior_acta_num"] is None
    finally:
        db.session.rollback()


def test_historial_no_usa_comprobacion_origen(app_ctx) -> None:
    try:
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
        act = Actuaciones(
            fecha=date(2026, 3, 1),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            notificacion_id=noti.id,
            comprobacion_id=comp_origen.id,
            tipo="INSPECCION",
        )
        db.session.add(act)
        db.session.flush()

        row = _row_for_act(act)
        assert row["comprobacion_posterior_acta_num"] is None
    finally:
        db.session.rollback()
