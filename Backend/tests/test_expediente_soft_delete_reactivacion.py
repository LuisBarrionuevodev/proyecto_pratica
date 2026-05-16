"""Reactivación de expedientes soft-deleted en el mismo circuito (respuesta oficio y prórroga notificación)."""

from __future__ import annotations

import random
from datetime import date, datetime, timezone

import pytest

from app.database import db
from app.domains.actuaciones.services.expediente_completion_service import complete_expediente_from_actuacion
from app.domains.actuaciones.services.notificacion_plazo_expediente_edit_service import (
    delete_notificacion_prorroga_expediente,
)
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion
from app.domains.actuaciones.services.oficio_completion_service import complete_oficio_from_actuacion
from app.models import Actuaciones, Comprobacion, Domicilio, Expediente, JuzgadoCatalogo, Notificacion, OrdenTrabajo


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _actuacion_comprobacion_con_domicilio() -> tuple[Actuaciones, JuzgadoCatalogo]:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="ReactivaOficio", numero="1")
    db.session.add(dom)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=3, motivo="test reactiva oficio")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 15),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    j = JuzgadoCatalogo(codigo=f"j_{_unique_num()[:8]}", nombre=f"Juz {_unique_num()[:8]}")
    db.session.add(j)
    db.session.flush()
    return act, j


def _setup_comp_only() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=5)
    db.session.add(ot)
    db.session.flush()
    comp = Comprobacion(numero_acta=_unique_num(), anio=2026, mes=5, motivo="dup test")
    db.session.add(comp)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 5, 1),
        mes=5,
        anio=2026,
        orden_trabajo_id=ot.id,
        comprobacion_id=comp.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_complete_oficio_reactiva_expediente_respuesta_mismo_id(app_ctx) -> None:
    act, juz = _actuacion_comprobacion_con_domicilio()
    db.session.commit()

    complete_expediente_from_actuacion(
        act.id,
        {"expediente_numero": _unique_num()[:6], "fecha_expediente": "2026-03-18"},
    )

    num_resp = _unique_num()[:6]
    payload = {
        "numero_oficio": f"OF-{_unique_num()[:4]}",
        "fecha_oficio": date(2026, 4, 1),
        "juzgado_id": juz.id,
        "numero_expediente_oficio": num_resp,
        "fecha_expediente_oficio": date(2026, 4, 1),
    }
    r1 = complete_oficio_from_actuacion(act.id, payload)
    ex_r1 = r1["expediente_respuesta_oficio"]
    oid = r1["oficio"].id
    ex_r1.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex_r1)
    db.session.commit()

    r2 = complete_oficio_from_actuacion(act.id, payload)
    ex_r2 = r2["expediente_respuesta_oficio"]
    assert ex_r2.id == ex_r1.id
    assert ex_r2.deleted_at is None
    assert ex_r2.oficio_id == oid
    assert ex_r2.tipo_expediente == "RESPUESTA_OFICIO"


def _actuacion_notificacion() -> Actuaciones:
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(ot)
    db.session.flush()
    dom = Domicilio(calle="ReactivaNoti", numero="2")
    db.session.add(dom)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=3)
    db.session.add(noti)
    db.session.flush()
    inicializar_timing_notificacion(noti, fecha_notificacion=date(2026, 3, 1))
    db.session.add(noti)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 3, 1),
        mes=3,
        anio=2026,
        orden_trabajo_id=ot.id,
        notificacion_id=noti.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    return act


def test_complete_expediente_prorroga_reactiva_mismo_id(app_ctx) -> None:
    act = _actuacion_notificacion()
    db.session.commit()

    num = _unique_num()[:6]
    complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": num,
            "fecha_expediente": "2026-03-10",
            "prorroga_dias": 4,
        },
    )
    ex1 = Expediente.query.filter_by(notificacion_id=act.notificacion_id, deleted_at=None).one()
    delete_notificacion_prorroga_expediente(act.id, ex1.id)

    act_ref = Actuaciones.query.get(act.id)
    assert act_ref is not None
    noti = db.session.get(Notificacion, act_ref.notificacion_id)
    assert noti is not None
    assert (noti.prorroga_dias or 0) == 0

    r2 = complete_expediente_from_actuacion(
        act.id,
        {
            "expediente_numero": num,
            "fecha_expediente": "2026-03-10",
            "prorroga_dias": 7,
        },
    )
    ex2 = r2["expediente"]
    assert ex2.id == ex1.id
    assert ex2.deleted_at is None
    assert ex2.prorroga_dias_otorgados == 7
    db.session.refresh(noti)
    assert noti.prorroga_dias == 7


def test_complete_expediente_envio_bloquea_si_otro_activo_mismo_numero(app_ctx) -> None:
    """Conflicto real: mismo número/año vigente en otro expediente (otra comprobación)."""
    act_a = _setup_comp_only()
    act_b = _setup_comp_only()
    db.session.commit()
    num = _unique_num()[:6]
    complete_expediente_from_actuacion(
        act_b.id,
        {"expediente_numero": num, "fecha_expediente": "2026-05-01"},
    )
    complete_expediente_from_actuacion(
        act_a.id,
        {"expediente_numero": _unique_num()[:6], "fecha_expediente": "2026-05-02"},
    )
    ex_del = (
        Expediente.query.filter_by(comprobacion_id=act_a.comprobacion_id, oficio_id=None)
        .filter(Expediente.deleted_at.is_(None))
        .first()
    )
    assert ex_del is not None
    ex_del.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex_del)
    db.session.commit()

    with pytest.raises(RuntimeError, match="ya existe"):
        complete_expediente_from_actuacion(
            act_a.id,
            {"expediente_numero": num, "fecha_expediente": "2026-05-01"},
        )

