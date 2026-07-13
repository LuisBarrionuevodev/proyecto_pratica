"""PR8.x: filtros de recorrido/historial (mes/año acta, oficio, expediente, tipo final)."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_resumen_row,
    resultado_cumplimiento_recorrido,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import list_comprobacion_recorrido
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    Expediente,
    Notificacion,
    Oficio,
    OrdenTrabajo,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_notificacion_act(mes: int, anio: int, fecha_act: date) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), mes=mes, anio=anio)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), mes=mes, anio=anio)
    db.session.add(noti)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_act,
        mes=fecha_act.month,
        anio=fecha_act.year,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def _mk_comprobacion_act(
    *,
    comp_mes: int,
    comp_anio: int,
    fecha_act: date,
    distrito_id: int | None = 1,
) -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), mes=comp_mes, anio=comp_anio)
    db.session.add(ot)
    db.session.flush()
    contrib = Contribuyente(apellido="Test", nombre="Comp", documento=_unique_num())
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(
        calle="Av Recorrido",
        numero="200",
        cp="2000",
        ciudad="Rosario",
        provincia="Santa Fe",
        pais="Argentina",
        contribuyente_id=contrib.id,
        distrito_id=distrito_id,
    )
    db.session.add(dom)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), mes=comp_mes, anio=comp_anio, motivo="filtro test")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=fecha_act,
        mes=fecha_act.month,
        anio=fecha_act.year,
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        comprobacion_id=comp.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_historial_notificacion_mes_anio_filtra_por_acta_no_por_fecha_actuacion(app_ctx) -> None:
    """Mes/año del acta de notificación, no ``Actuaciones.fecha``."""
    try:
        act_jul = _mk_notificacion_act(mes=7, anio=2026, fecha_act=date(2025, 1, 15))
        act_ene = _mk_notificacion_act(mes=1, anio=2026, fecha_act=date(2026, 7, 10))
        fl = ActuacionesPendientesFilters.model_validate(
            {"source_type": "notificacion", "mes": 7, "anio": 2026}
        )
        ids = {a.id for a in get_pendientes_expediente(fl)}
        assert act_jul.id in ids
        assert act_ene.id not in ids
    finally:
        db.session.rollback()


def test_recorrido_comprobacion_mes_anio_filtra_por_acta(app_ctx) -> None:
    try:
        act_abr = _mk_comprobacion_act(comp_mes=4, comp_anio=2024, fecha_act=date(2023, 12, 1))
        act_may = _mk_comprobacion_act(comp_mes=5, comp_anio=2024, fecha_act=date(2024, 4, 20))
        fl = ActuacionesPendientesFilters.model_validate({"mes": 4, "anio": 2024})
        ids = {a.id for a in list_comprobacion_recorrido(fl)}
        assert act_abr.id in ids
        assert act_may.id not in ids
    finally:
        db.session.rollback()


def test_recorrido_distrito_filtra_por_domicilio(app_ctx) -> None:
    try:
        act_d1 = _mk_comprobacion_act(
            comp_mes=6, comp_anio=2026, fecha_act=date(2026, 6, 1), distrito_id=1
        )
        act_d2 = _mk_comprobacion_act(
            comp_mes=6, comp_anio=2026, fecha_act=date(2026, 6, 2), distrito_id=2
        )
        fl = ActuacionesPendientesFilters.model_validate(
            {"omitir_rango_fecha": True, "distrito_id": 1}
        )
        ids = {a.id for a in list_comprobacion_recorrido(fl)}
        assert act_d1.id in ids
        assert act_d2.id not in ids
    finally:
        db.session.rollback()


def test_recorrido_filtra_por_segundo_oficio_y_expediente_respuesta(app_ctx) -> None:
    try:
        act = _mk_comprobacion_act(comp_mes=6, comp_anio=2026, fecha_act=date(2026, 6, 1))
        cid = int(act.comprobacion_id)
        ofi1 = Oficio(
            comprobacion_id=cid,
            numero_oficio=f"O1{_unique_num()[:4]}",
            anio=2026,
            fecha_oficio=date(2026, 6, 5),
        )
        ofi2 = Oficio(
            comprobacion_id=cid,
            numero_oficio=f"O2{_unique_num()[:4]}",
            anio=2026,
            fecha_oficio=date(2026, 6, 10),
        )
        db.session.add_all([ofi1, ofi2])
        db.session.flush()
        db.session.add(
            Expediente(
                comprobacion_id=cid,
                oficio_id=ofi1.id,
                numero_expediente="012388",
                anio=2026,
                fecha_expediente=date(2026, 6, 11),
                tipo_expediente="RESPUESTA_OFICIO",
            )
        )
        db.session.add(
            Expediente(
                comprobacion_id=cid,
                oficio_id=ofi2.id,
                numero_expediente="012389",
                anio=2026,
                fecha_expediente=date(2026, 6, 12),
                tipo_expediente="RESPUESTA_OFICIO",
            )
        )
        db.session.flush()

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        by_oficio = list_comprobacion_recorrido(fl, oficio_numero=ofi2.numero_oficio)
        assert act.id in {a.id for a in by_oficio}

        for query in ("012389", "012389/2026", "12389"):
            by_exp = list_comprobacion_recorrido(fl, expediente_numero=query)
            assert act.id in {a.id for a in by_exp}, f"falló con query={query!r}"

        row = comprobacion_recorrido_resumen_row(act)
        resumen = row.get("oficios_resumen") or []
        assert len(resumen) == 2
        assert resumen[0].get("expediente_texto") == "012388/2026"
        assert resumen[1].get("expediente_texto") == "012389/2026"
        assert "012388/2026" in (row.get("oficios_texto") or "")
        assert "012389/2026" in (row.get("oficios_texto") or "")
    finally:
        db.session.rollback()


def test_recorrido_tipo_final_filtra_por_resultado(app_ctx) -> None:
    try:
        act_c = _mk_comprobacion_act(comp_mes=8, comp_anio=2026, fecha_act=date(2026, 8, 1))
        act_c.resultado_cumplimiento_oficio = "CUMPLE"
        act_n = _mk_comprobacion_act(comp_mes=8, comp_anio=2026, fecha_act=date(2026, 8, 2))
        act_n.resultado_cumplimiento_oficio = "NO_CUMPLE"
        db.session.flush()

        fl = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        cumple = list_comprobacion_recorrido(fl, tipo_final="CUMPLE")
        ids = {a.id for a in cumple}
        assert act_c.id in ids
        assert act_n.id not in ids
        assert resultado_cumplimiento_recorrido(act_c) == "CUMPLE"
    finally:
        db.session.rollback()
