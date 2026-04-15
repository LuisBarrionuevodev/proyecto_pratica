"""
Bandeja GET pendientes/expediente: rama NOTIFICACION con 0..N PRORROGA_NOTIFICACION.

COMPROBACION mantiene criterio sin expediente de envío. Requiere BD; rollback al final.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

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
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    get_pendientes_expediente,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, Motivo, Notificacion, OrdenTrabajo


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


def _rows_expediente(acts: list[Actuaciones]) -> list[dict]:
    plazos, venc = build_notificacion_expediente_bandeja_metrics(acts)
    return [
        actuacion_to_pendiente_expediente_row(
            a,
            plazos_por_notificacion=plazos,
            fecha_vencimiento_por_notificacion=venc,
        )
        for a in acts
    ]


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
        assert row["dias_restantes"] == 5
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
        row0 = next(r for r in _rows_expediente(acts0) if r["id"] == act.id)
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
    finally:
        db.session.rollback()
