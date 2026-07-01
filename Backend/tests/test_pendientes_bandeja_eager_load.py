"""Eager-load en queries base de bandejas documentales (sin N+1 en presenter)."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest
from sqlalchemy import inspect as sa_inspect

from app.database import db
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
)
from app.domains.actuaciones.services.notificacion_timing_service import (
    inicializar_timing_notificacion,
)
from app.domains.actuaciones.services.pendientes_service import (
    get_pendientes_expediente,
    get_pendientes_oficio,
)
from app.models import Actuaciones, Comprobacion, Contribuyente, Domicilio, IniciadorRuta, Notificacion, OrdenTrabajo, Rubro, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


_BANDEJA_RELATIONS = (
    "orden_trabajo",
    "domicilio",
    "inspeccion",
    "clausura",
    "decomiso",
    "notificacion",
    "comprobacion",
    "inspector",
)


def _assert_bandeja_relations_loaded(act: Actuaciones) -> None:
    insp = sa_inspect(act)
    unloaded = set(insp.unloaded)
    for rel in _BANDEJA_RELATIONS:
        assert rel not in unloaded, f"{rel} debería estar eager-loaded"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _filters(source_type: str) -> ActuacionesPendientesFilters:
    return ActuacionesPendientesFilters.model_validate(
        {
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "source_type": source_type,
        }
    )


def _mk_actuacion_con_domicilio(*, with_noti: bool, with_comp: bool) -> Actuaciones:
    rubro = Rubro(nombre=f"rubro-{_unique_num()}")
    contrib = Contribuyente(apellido="Pérez", nombre="Ana", documento=_unique_num())
    db.session.add_all([rubro, contrib])
    db.session.flush()
    dom = Domicilio(
        calle="Calle Test",
        numero="123",
        cp="5000",
        ciudad="Córdoba",
        provincia="Córdoba",
        pais="AR",
        rubro_id=rubro.id,
        contribuyente_id=contrib.id,
    )
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    noti_id = None
    comp_id = None
    if with_noti:
        noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
        db.session.add(noti)
        db.session.flush()
        inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
        noti_id = noti.id
    if with_comp:
        comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="motivo test eager")
        db.session.add(comp)
        db.session.flush()
        comp_id = comp.id
    act = Actuaciones(
        fecha=date(2026, 3, 10),
        mes=3,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        notificacion_id=noti_id,
        comprobacion_id=comp_id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_pendientes_expediente_notificacion_eager_load(app_ctx) -> None:
    try:
        act = _mk_actuacion_con_domicilio(with_noti=True, with_comp=False)
        acts = get_pendientes_expediente(_filters("notificacion"))
        assert any(a.id == act.id for a in acts)
        target = next(a for a in acts if a.id == act.id)
        _assert_bandeja_relations_loaded(target)
    finally:
        db.session.rollback()


def test_pendientes_expediente_comprobacion_eager_load(app_ctx) -> None:
    try:
        act = _mk_actuacion_con_domicilio(with_noti=False, with_comp=True)
        acts = get_pendientes_expediente(_filters("comprobacion"))
        assert any(a.id == act.id for a in acts)
        target = next(a for a in acts if a.id == act.id)
        _assert_bandeja_relations_loaded(target)
    finally:
        db.session.rollback()


def test_pendientes_oficio_eager_load(app_ctx) -> None:
    from app.domains.actuaciones.services.expediente_completion_service import (
        complete_expediente_from_actuacion,
    )

    try:
        act = _mk_actuacion_con_domicilio(with_noti=False, with_comp=True)
        complete_expediente_from_actuacion(
            act.id,
            {
                "expediente_numero": _unique_num(),
                "fecha_expediente": "2026-03-20",
                "source_type": "COMPROBACION",
            },
        )
        acts = get_pendientes_oficio(_filters("comprobacion"))
        assert any(a.id == act.id for a in acts)
        target = next(a for a in acts if a.id == act.id)
        _assert_bandeja_relations_loaded(target)
    finally:
        db.session.rollback()


def test_pendientes_notificacion_reinspeccion_eager_load(app_ctx) -> None:
    """GET pendientes-notificacion usa list_reinspeccion_notificacion_operativas."""
    try:
        user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        assert user is not None
        act = _mk_actuacion_con_domicilio(with_noti=True, with_comp=False)
        noti = db.session.get(Notificacion, act.notificacion_id)
        assert noti is not None
        noti.fecha_vencimiento = date.today() - timedelta(days=1)
        ini = IniciadorRuta(
            tipo_iniciador="REINSPECCION_NOTIFICACION",
            estado_iniciador="PENDIENTE",
            actuacion_id=act.id,
            notificacion_id=noti.id,
            domicilio_id=act.domicilio_id,
            fecha_origen=date(2026, 3, 10),
            anio=2026,
            mes=3,
            created_by_user_id=int(user.id),
        )
        db.session.add(ini)
        db.session.flush()
        acts = list_reinspeccion_notificacion_operativas()
        assert any(a.id == act.id for a in acts)
        target = next(a for a in acts if a.id == act.id)
        _assert_bandeja_relations_loaded(target)
    finally:
        db.session.rollback()
