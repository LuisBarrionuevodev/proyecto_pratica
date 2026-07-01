"""Presenter bandeja notificación: prorroga_dias, dias_restantes y DELETE recalculado."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_iniciador_service import list_reinspeccion_notificacion_operativas
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    delete_notificacion_prorroga_expediente,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.pendientes_service import build_notificacion_expediente_bandeja_metrics
from app.models import Actuaciones, Domicilio, Expediente, Notificacion, OrdenTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _row(act: Actuaciones) -> dict:
    acts = [act]
    plazos, venc, prorroga_dias = build_notificacion_expediente_bandeja_metrics(acts)
    return actuacion_to_pendiente_expediente_row(
        act,
        plazos_por_notificacion=plazos,
        fecha_vencimiento_por_notificacion=venc,
        prorroga_dias_por_notificacion=prorroga_dias,
        expediente_list_channel="notificacion",
    )


def _mk_act_noti() -> tuple[Actuaciones, Notificacion]:
    user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    assert user is not None
    dom = Domicilio(calle="PresenterPlazo", numero="1")
    db.session.add(dom)
    db.session.flush()
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
        domicilio_id=dom.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    return act, noti


def test_presenter_expone_prorroga_dias_y_dias_restantes_tras_alta(app_ctx) -> None:
    try:
        act, noti = _mk_act_noti()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 5).isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 10,
            },
        )
        db.session.refresh(noti)
        row = _row(act)
        assert row["notificacion_prorroga_dias"] == 10
        assert row["plazos_otorgados"] == 1
        assert row["dias_restantes"] is not None
        assert int(row["dias_restantes"]) >= 0
    finally:
        db.session.rollback()


def test_delete_expediente_devuelve_plazo_recalculado_y_no_lista_soft_deleted(app_ctx) -> None:
    try:
        act, noti = _mk_act_noti()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date(2026, 3, 5).isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 7,
            },
        )
        ex = (
            Expediente.query.filter(Expediente.notificacion_id == noti.id)
            .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .one()
        )
        out = delete_notificacion_prorroga_expediente(act.id, ex.id)
        assert out["plazo_notificacion"]["prorroga_total_dias"] == 0
        db.session.refresh(noti)
        assert int(noti.prorroga_dias or 0) == 0
        row = _row(act)
        assert row["notificacion_prorroga_dias"] == 0
        assert row["plazos_otorgados"] == 0
        activos = (
            Expediente.query.filter(Expediente.notificacion_id == noti.id)
            .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
            .filter(Expediente.deleted_at.is_(None))
            .count()
        )
        assert activos == 0
    finally:
        db.session.rollback()


def test_pendiente_reinspeccion_presenter_conserva_plazo(app_ctx) -> None:
    try:
        act, noti = _mk_act_noti()
        noti.fecha_vencimiento = date.today()
        db.session.add(noti)
        db.session.flush()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 5,
            },
        )
        db.session.refresh(noti)
        operativas = list_reinspeccion_notificacion_operativas()
        ids = {a.id for a in operativas}
        if act.id in ids:
            row = _row(act)
            assert row["notificacion_prorroga_dias"] == 5
    finally:
        db.session.rollback()
