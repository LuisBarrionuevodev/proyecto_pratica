"""Prórroga desde Pendiente Reinspección: recalcula vencimiento, revoca iniciador, bandejas."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_pendiente_expediente_row
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.pendientes_service import (
    build_notificacion_expediente_bandeja_metrics,
    get_pendientes_expediente,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.models import Actuaciones, Contribuyente, Domicilio, IniciadorRuta, Notificacion, OrdenTrabajo, User


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
        {"source_type": "notificacion", "desde": "2020-01-01", "hasta": "2099-12-31"}
    )


def _mk_vencida_con_iniciador() -> tuple[Actuaciones, Notificacion, IniciadorRuta]:
    user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    assert user is not None
    contrib = Contribuyente(apellido="Prorroga", nombre="Test", documento=_unique_num())
    db.session.add(contrib)
    db.session.flush()
    dom = Domicilio(calle="CalleProrroga", numero="1", contribuyente_id=contrib.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    today = date.today()
    inicializar_timing_notificacion(noti, fecha_notificacion=today - timedelta(days=20))
    noti.fecha_vencimiento = today
    act = Actuaciones(
        fecha=date(2026, 1, 2),
        mes=1,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
        tipo="INSPECCION",
    )
    db.session.add(act)
    db.session.flush()
    ini = IniciadorRuta(
        actuacion_id=act.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="PENDIENTE",
        fecha_origen=date(2026, 1, 2),
        anio=2026,
        mes=1,
        created_by_user_id=int(user.id),
    )
    db.session.add(ini)
    db.session.flush()
    return act, noti, ini


def _pendientes_reinspeccion_ids() -> set[int]:
    return {a.id for a in list_reinspeccion_notificacion_operativas()}


def _en_plazo_ids() -> set[int]:
    acts = get_pendientes_expediente(_filters_notificacion())
    plazos, venc = build_notificacion_expediente_bandeja_metrics(acts)
    out: set[int] = set()
    for act in acts:
        row = actuacion_to_pendiente_expediente_row(
            act,
            plazos_por_notificacion=plazos,
            fecha_vencimiento_por_notificacion=venc,
            expediente_list_channel="notificacion",
        )
        dias = row.get("dias_restantes")
        if dias is not None and int(dias) >= 5:
            out.add(int(act.id))
    return out


def test_prorroga_en_plazo_sigue_funcionando(app_ctx) -> None:
    try:
        act, noti, _ini = _mk_vencida_con_iniciador()
        result = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 5,
            },
        )
        db.session.refresh(noti)
        assert noti.fecha_vencimiento is not None
        assert int(noti.prorroga_dias or 0) == 5
        if noti.fecha_vencimiento and noti.fecha_vencimiento > date.today():
            assert result["next_state_hint"] == "EN_PLAZO"
        else:
            assert result["next_state_hint"] == "PENDIENTE_REINSPECCION"
    finally:
        db.session.rollback()


def test_prorroga_desde_pendiente_reinspeccion_recuenta_y_sale_de_bandeja(app_ctx) -> None:
    try:
        act, noti, ini = _mk_vencida_con_iniciador()
        assert act.id in _pendientes_reinspeccion_ids()

        result = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 15,
            },
        )
        db.session.refresh(noti)
        db.session.refresh(ini)
        assert noti.fecha_vencimiento is not None
        assert noti.fecha_vencimiento > date.today()
        assert act.id not in _pendientes_reinspeccion_ids()
        assert ini.estado_iniciador == "ANULADO"
        assert result["next_state_hint"] == "EN_PLAZO"
        assert int(result.get("revoked_reinspeccion_iniciadores") or 0) >= 1
    finally:
        db.session.rollback()


def test_prorroga_vigente_aparece_en_bandeja_en_plazo(app_ctx) -> None:
    try:
        act, noti, _ini = _mk_vencida_con_iniciador()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 15,
            },
        )
        db.session.refresh(noti)
        assert act.id in _en_plazo_ids()
    finally:
        db.session.rollback()


def test_prorroga_insuficiente_permanece_en_pendiente_reinspeccion(app_ctx) -> None:
    try:
        act, noti, ini = _mk_vencida_con_iniciador()
        result = complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 0,
            },
        )
        db.session.refresh(noti)
        db.session.refresh(ini)
        assert noti.fecha_vencimiento is not None
        assert noti.fecha_vencimiento <= date.today()
        assert act.id in _pendientes_reinspeccion_ids()
        assert ini.estado_iniciador == "PENDIENTE"
        assert result["next_state_hint"] == "PENDIENTE_REINSPECCION"
        assert int(result.get("revoked_reinspeccion_iniciadores") or 0) == 0
    finally:
        db.session.rollback()


def test_prorroga_no_duplica_iniciador_pendiente(app_ctx) -> None:
    try:
        act, noti, ini = _mk_vencida_con_iniciador()
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": date.today().isoformat(),
                "source_type": "NOTIFICACION",
                "prorroga_dias": 0,
            },
        )
        db.session.refresh(ini)
        assert ini.estado_iniciador == "PENDIENTE"

        before_sync = IniciadorRuta.query.filter_by(
            notificacion_id=noti.id,
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            deleted_at=None,
        ).count()
        sync_iniciadores_reinspeccion_notificacion()
        after_sync = IniciadorRuta.query.filter_by(
            notificacion_id=noti.id,
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            deleted_at=None,
        ).count()
        assert before_sync == after_sync == 1
    finally:
        db.session.rollback()
