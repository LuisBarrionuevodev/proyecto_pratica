"""
Bandeja GET pendientes/expediente: rama NOTIFICACION con 0..N PRORROGA_NOTIFICACION.

COMPROBACION mantiene criterio sin expediente de envío. Requiere BD; rollback al final.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_pendiente_expediente_row,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.expediente_completion_service import (
    complete_expediente_from_actuacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    build_posterior_comprobacion_por_actuacion_id,
    build_reinspeccion_comprobacion_por_actuacion_id,
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Motivo, Notificacion, OrdenTrabajo
from app.shared.utils.business_days_ar import contar_dias_habiles_inclusive


def _unique_num() -> str:
    return uuid4().hex[:6].upper()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _filters_notificacion() -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": "notificacion",
        }
    )


def _filters_comprobacion() -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": "comprobacion",
        }
    )


def _mk_actuacion_solo_notificacion() -> tuple[Actuaciones, Notificacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(
        numero_acta=_unique_num(),
        anio=2026,
        mes=3,
    )
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, noti


def _mk_actuacion_solo_comprobacion() -> tuple[Actuaciones, Comprobacion]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="test comp bandeja")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
    )
    db.session.add(act)
    db.session.flush()
    return act, comp


def test_notificacion_y_comprobacion_misma_actuacion_aparece_en_ambas_bandas(app_ctx) -> None:
    """PR1: misma actuación con ambas actas entra en bandeja notificación (plazo) y en comprobación."""
    try:
        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()
        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(noti)
        db.session.flush()
        inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="motivo mixto bandeja")
        db.session.add(comp)
        db.session.flush()
        act = Actuaciones(
            fecha=date(2026, 3, 2),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot.id,
            notificacion_id=noti.id,
            comprobacion_id=comp.id,
        )
        db.session.add(act)
        db.session.flush()

        acts_n = get_pendientes_expediente(_filters_notificacion())
        assert act.id in [a.id for a in acts_n]
        row_n = next(r for r in _rows_expediente(acts_n, channel="notificacion") if r["id"] == act.id)
        assert row_n["source_type"] == "NOTIFICACION"
        assert row_n["notificacion_id"] == noti.id
        assert row_n["comprobacion_id"] == comp.id
        assert row_n["plazos_otorgados"] == 0
        assert row_n["dias_restantes"] is not None
        assert row_n["comprobacion_posterior_acta_num"] is None

        acts_c = get_pendientes_expediente(_filters_comprobacion())
        assert act.id in [a.id for a in acts_c]
        row_c = next(r for r in _rows_expediente(acts_c, channel="comprobacion") if r["id"] == act.id)
        assert row_c["source_type"] == "COMPROBACION"
        assert row_c["dias_restantes"] is None
        assert row_c["plazos_otorgados"] is None
    finally:
        db.session.rollback()


def _rows_expediente(acts: list[Actuaciones], *, channel: str = "notificacion") -> list[dict]:
    plazos, venc, prorroga_dias = build_notificacion_expediente_bandeja_metrics(acts)
    posterior = build_posterior_comprobacion_por_actuacion_id(acts)
    reinspeccion_comp = build_reinspeccion_comprobacion_por_actuacion_id(acts)
    counts_by_eo = build_counts_by_eo_from_actuaciones(acts)
    return [
        actuacion_to_pendiente_expediente_row(
            a,
            plazos_por_notificacion=plazos,
            fecha_vencimiento_por_notificacion=venc,
            prorroga_dias_por_notificacion=prorroga_dias,
            counts_by_eo=counts_by_eo,
            posterior_por_actuacion_id=posterior,
            reinspeccion_comprobacion_por_actuacion_id=reinspeccion_comp,
            expediente_list_channel=channel,
        )
        for a in acts
    ]


def test_notificacion_reinspeccion_comprobacion_en_historial(app_ctx) -> None:
    """Historial: comprobación posterior = la de REINSPECCION, no la origen ni otra del domicilio."""
    try:
        contrib = Contribuyente(apellido="ReinApellido", nombre="Ana", documento=_unique_num())
        db.session.add(contrib)
        db.session.flush()
        dom = Domicilio(calle="CalleRein", numero="50", contribuyente_id=contrib.id)
        db.session.add(dom)
        db.session.flush()

        act_noti, noti = _mk_actuacion_solo_notificacion()
        act_noti.domicilio_id = dom.id
        act_noti.fecha = date(2026, 3, 1)
        noti.fecha_vencimiento = date.today() + timedelta(days=10)
        db.session.flush()

        comp_origen = Comprobacion(numero_acta="ORIG01", anio=2026, mes=3, motivo="origen mixto")
        db.session.add(comp_origen)
        db.session.flush()
        act_noti.comprobacion_id = comp_origen.id
        db.session.flush()

        ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot2)
        db.session.flush()
        comp_rein = Comprobacion(numero_acta="REIN99", anio=2026, mes=3, motivo="reinspeccion test")
        db.session.add(comp_rein)
        db.session.flush()
        act_rein = Actuaciones(
            fecha=date(2026, 3, 20),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot2.id,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
            comprobacion_id=comp_rein.id,
            tipo="REINSPECCION",
        )
        db.session.add(act_rein)
        db.session.flush()

        acts = get_pendientes_expediente(_filters_notificacion())
        row = next(r for r in _rows_expediente(acts) if r["id"] == act_noti.id)
        assert row["comprobacion_posterior_fecha"] == "2026-03-20"
        assert row["comprobacion_posterior_acta_num"] == "REIN99"
        assert row["comprobacion_posterior_acta_num"] != comp_origen.numero_acta
    finally:
        db.session.rollback()


def test_notificacion_sin_reinspeccion_no_muestra_comprobacion_domicilio(app_ctx) -> None:
    """Sin REINSPECCION con comprobación: no se infiere comprobación posterior por domicilio."""
    try:
        contrib = Contribuyente(apellido="PosteriorApellido", nombre="Ana", documento=_unique_num())
        db.session.add(contrib)
        db.session.flush()
        dom = Domicilio(calle="CallePosterior", numero="50", contribuyente_id=contrib.id)
        db.session.add(dom)
        db.session.flush()

        act_noti, noti = _mk_actuacion_solo_notificacion()
        act_noti.domicilio_id = dom.id
        act_noti.fecha = date(2026, 3, 1)
        noti.fecha_vencimiento = date.today() + timedelta(days=10)
        db.session.flush()

        ot2 = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot2)
        db.session.flush()
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="otra visita")
        db.session.add(comp)
        db.session.flush()
        act_comp = Actuaciones(
            fecha=date(2026, 3, 20),
            mes=3,
            anio=2026,
            orden_trabajo_id=ot2.id,
            domicilio_id=dom.id,
            comprobacion_id=comp.id,
        )
        db.session.add(act_comp)
        db.session.flush()

        acts = get_pendientes_expediente(_filters_notificacion())
        row = next(r for r in _rows_expediente(acts) if r["id"] == act_noti.id)
        assert row["comprobacion_posterior_fecha"] is None
        assert row["comprobacion_posterior_acta_num"] is None
    finally:
        db.session.rollback()


def test_notificacion_cero_expedientes_aparece_plazos_cero(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        noti.fecha_vencimiento = date.today() + timedelta(days=5)
        db.session.flush()
        fl = _filters_notificacion()
        acts = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts]
        row = next(r for r in _rows_expediente(acts) if r["id"] == act.id)
        assert row["source_type"] == "NOTIFICACION"
        assert row["plazos_otorgados"] == 0
        assert row["dias_restantes"] == contar_dias_habiles_inclusive(
            date.today(), noti.fecha_vencimiento
        )
    finally:
        db.session.rollback()


def test_notificacion_un_expediente_sigue_en_lista(app_ctx) -> None:
    try:
        act, _noti = _mk_actuacion_solo_notificacion()
        db.session.flush()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 10),
                "prorroga_dias": 2,
            },
        )
        fl = _filters_notificacion()
        acts = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts]
        row = next(r for r in _rows_expediente(acts) if r["id"] == act.id)
        assert row["plazos_otorgados"] == 1
    finally:
        db.session.rollback()


def test_notificacion_dos_expedientes_sigue_en_lista_plazos_dos(app_ctx) -> None:
    try:
        act, _noti = _mk_actuacion_solo_notificacion()
        db.session.flush()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 10),
                "prorroga_dias": 1,
            },
        )
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 4, 1),
                "prorroga_dias": 3,
            },
        )
        fl = _filters_notificacion()
        acts = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts]
        row = next(r for r in _rows_expediente(acts) if r["id"] == act.id)
        assert row["plazos_otorgados"] == 2
    finally:
        db.session.rollback()


def test_notificacion_dias_restantes_vencido_es_cero(app_ctx) -> None:
    try:
        act, noti = _mk_actuacion_solo_notificacion()
        noti.fecha_vencimiento = date.today() - timedelta(days=3)
        db.session.flush()
        fl = _filters_notificacion()
        acts = get_pendientes_expediente(fl)
        row = next(r for r in _rows_expediente(acts) if r["id"] == act.id)
        assert row["dias_restantes"] == 0
    finally:
        db.session.rollback()


def test_notificacion_filtros_documentales_post_query(app_ctx) -> None:
    """Rama NOTIFICACION: contribuyente_q / calle_q / numero_notificacion / motivo_q reducen el set."""
    try:
        contrib = Contribuyente(apellido="DocFilterApellido", nombre="Pepe", documento=_unique_num())
        db.session.add(contrib)
        db.session.flush()
        dom = Domicilio(calle="CalleDocFilterXyz", numero="200", contribuyente_id=contrib.id)
        db.session.add(dom)
        db.session.flush()
        act, noti = _mk_actuacion_solo_notificacion()
        act.domicilio_id = dom.id
        noti.numero_acta = "777666"
        noti.fecha_vencimiento = date.today() + timedelta(days=4)
        mot = Motivo(nombre="InfraccionDocFilterTipo")
        db.session.add(mot)
        db.session.flush()
        noti.motivos.append(mot)
        db.session.flush()

        base = {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": "notificacion",
        }
        assert act.id in [a.id for a in get_pendientes_expediente(ActuacionesPendientesFilters.model_validate(base))]

        assert act.id in [
            a.id
            for a in get_pendientes_expediente(
                ActuacionesPendientesFilters.model_validate({**base, "contribuyente_q": "DocFilterApellido"})
            )
        ]
        assert act.id in [
            a.id
            for a in get_pendientes_expediente(
                ActuacionesPendientesFilters.model_validate({**base, "calle_q": "DocFilterXyz"})
            )
        ]
        assert act.id in [
            a.id
            for a in get_pendientes_expediente(
                ActuacionesPendientesFilters.model_validate({**base, "numero_notificacion": "776"})
            )
        ]
        assert act.id in [
            a.id
            for a in get_pendientes_expediente(
                ActuacionesPendientesFilters.model_validate({**base, "motivo_q": "DocFilterTipo"})
            )
        ]
        assert act.id not in [
            a.id
            for a in get_pendientes_expediente(
                ActuacionesPendientesFilters.model_validate({**base, "contribuyente_q": "NOEXISTE999"})
            )
        ]
    finally:
        db.session.rollback()


def test_comprobacion_no_aplica_filtros_documentales(app_ctx) -> None:
    """Los query params documentales no filtran la rama COMPROBACION."""
    try:
        act, _comp = _mk_actuacion_solo_comprobacion()
        db.session.flush()
        fl = ActuacionesPendientesFilters.model_validate(
            {
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
                "source_type": "comprobacion",
                "contribuyente_q": "NOEXISTE999",
                "calle_q": "NOEXISTE888",
            }
        )
        acts = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts]
    finally:
        db.session.rollback()


def test_comprobacion_bandeja_sin_expediente_luego_excluida_metricas_none(app_ctx) -> None:
    try:
        act, _comp = _mk_actuacion_solo_comprobacion()
        db.session.flush()
        fl = _filters_comprobacion()
        acts0 = get_pendientes_expediente(fl)
        assert act.id in [a.id for a in acts0]
        row0 = next(r for r in _rows_expediente(acts0, channel="comprobacion") if r["id"] == act.id)
        assert row0["source_type"] == "COMPROBACION"
        assert row0["dias_restantes"] is None
        assert row0["plazos_otorgados"] is None

        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 20),
            },
        )
        acts1 = get_pendientes_expediente(fl)
        assert act.id not in [a.id for a in acts1]

        fl_ofi = ActuacionesPendientesFilters.model_validate({"omitir_rango_fecha": True})
        ofi_acts = get_pendientes_oficio(fl_ofi)
        assert act.id in [a.id for a in ofi_acts]
    finally:
        db.session.rollback()
