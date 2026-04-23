"""
PR3: INSPECCION con notificación vencida + comprobación misma actuación — elegibilidad y sync.

Requiere BD y al menos un User activo (sync usa created_by_user_id).
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    _eligible_inspecciones_vencidas,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.models import Actuaciones, Comprobacion, Domicilio, IniciadorRuta, Notificacion, OrdenTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_active_user() -> None:
    if User.query.filter(User.is_active.is_(True)).first():
        return
    u = User(
        username=f"pr3mix_{_unique_num()}",
        email=f"pr3mix_{_unique_num()}@test.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_inspeccion_mixta_vencida_es_elegible_y_sync_materializa_idempotente(app_ctx) -> None:
    try:
        _ensure_active_user()

        dom = Domicilio(calle="PR3MixCalle", numero="100")
        db.session.add(dom)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()

        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(noti)
        db.session.flush()
        noti.fecha_notificacion = date(2026, 1, 10)
        noti.fecha_vencimiento = date.today() - timedelta(days=2)
        noti.plazo_dias = 5
        noti.prorroga_dias = 0
        db.session.add(noti)
        db.session.flush()

        comp = Comprobacion(
            numero_acta=_unique_num(),
            anio=2026,
            mes=3,
            motivo="mix pr3 comprobacion",
        )
        db.session.add(comp)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 3, 5),
            mes=3,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
            comprobacion_id=comp.id,
        )
        db.session.add(act)
        db.session.flush()

        eligible = _eligible_inspecciones_vencidas()
        assert any(a.id == act.id for a in eligible), "actuación mixta debe ser elegible"

        o1 = sync_iniciadores_reinspeccion_notificacion()
        assert o1.created >= 1

        ini = (
            IniciadorRuta.query.filter(
                IniciadorRuta.notificacion_id == noti.id,
                IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
                IniciadorRuta.deleted_at.is_(None),
            )
            .order_by(IniciadorRuta.id.desc())
            .first()
        )
        assert ini is not None
        assert ini.actuacion_id == act.id
        assert "paralelo" in (ini.observaciones or "").lower()

        o2 = sync_iniciadores_reinspeccion_notificacion()
        assert o2.created == 0
        assert o2.skipped_already_blocking >= 1
    finally:
        db.session.rollback()


def test_inspeccion_solo_notificacion_sigue_elegible(app_ctx) -> None:
    try:
        _ensure_active_user()

        dom = Domicilio(calle="PR3SoloN", numero="101")
        db.session.add(dom)
        db.session.flush()

        ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(ot)
        db.session.flush()

        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(noti)
        db.session.flush()
        noti.fecha_notificacion = date(2026, 2, 1)
        noti.fecha_vencimiento = date.today() - timedelta(days=1)
        noti.plazo_dias = 5
        noti.prorroga_dias = 0
        db.session.add(noti)
        db.session.flush()

        act = Actuaciones(
            fecha=date(2026, 3, 1),
            mes=3,
            anio=2026,
            tipo="INSPECCION",
            orden_trabajo_id=ot.id,
            domicilio_id=dom.id,
            notificacion_id=noti.id,
        )
        db.session.add(act)
        db.session.flush()

        eligible = _eligible_inspecciones_vencidas()
        assert any(a.id == act.id for a in eligible)
    finally:
        db.session.rollback()
