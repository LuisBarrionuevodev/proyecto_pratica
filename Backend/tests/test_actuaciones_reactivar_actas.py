"""Reactivación de actas soft-deleted desde canal Actuaciones CRUD."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.domains.actuaciones.services.actas_quitar_canal_actas_service import quitar_acta_canal_actas
from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    Inspeccion,
    Motivo,
    Notificacion,
    OrdenTrabajo,
    Rubro,
)


def _ot_num() -> str:
    return f"{random.randint(0, 999999):06d}"


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_actuacion_base() -> tuple[Actuaciones, Rubro, str]:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    doc = str(random.randint(10_000_000, 99_999_999))
    c = Contribuyente(apellido="ReAct", nombre="Tit", documento=doc)
    db.session.add(c)
    db.session.flush()
    dom = Domicilio(calle=f"ReAct_{uuid4().hex[:6]}", numero="10", rubro_id=rub.id, contribuyente_id=c.id)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_ot_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 1),
        mes=6,
        anio=2026,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.commit()
    return act, rub, doc


def test_reactivar_notificacion_misma_acta(app_ctx) -> None:
    act, rub, doc = _mk_actuacion_base()
    acta_num = _ot_num()
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo")
    motivo_nombre = str(motivo.nombre)
    aplicar_payload_actuacion(
        act,
        {
            "notificacion": {"acta_num": acta_num, "motivos": [motivo_nombre]},
            "rubro_nombre": rub.nombre,
            "contribuyente": {"doc_nro": doc, "apellido": "ReAct", "nombre": "Tit"},
        },
    )
    db.session.commit()
    nid = act.notificacion_id
    assert nid is not None

    quitar_acta_canal_actas(act.id, "NOTIFICACION")
    db.session.expunge_all()
    act = db.session.get(Actuaciones, act.id)
    noti = db.session.get(Notificacion, nid)
    assert act is not None and act.notificacion_id is None
    assert noti is not None and noti.deleted_at is not None

    aplicar_payload_actuacion(
        act,
        {"notificacion": {"acta_num": acta_num, "motivos": [motivo_nombre]}},
    )
    db.session.commit()
    db.session.refresh(act)
    db.session.refresh(noti)
    assert act.notificacion_id == nid
    assert noti.deleted_at is None


def test_notificacion_nueva_tras_borrar_mantiene_anterior_inactiva(app_ctx) -> None:
    act, rub, doc = _mk_actuacion_base()
    acta_vieja = _ot_num()
    acta_nueva = _ot_num()
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo")
    motivo_nombre = str(motivo.nombre)
    aplicar_payload_actuacion(
        act,
        {"notificacion": {"acta_num": acta_vieja, "motivos": [motivo_nombre]}},
    )
    db.session.commit()
    nid_vieja = act.notificacion_id
    quitar_acta_canal_actas(act.id, "NOTIFICACION")

    aplicar_payload_actuacion(
        act,
        {"notificacion": {"acta_num": acta_nueva, "motivos": [motivo.nombre]}},
    )
    db.session.commit()
    assert act.notificacion_id != nid_vieja
    noti_vieja = db.session.get(Notificacion, nid_vieja)
    noti_nueva = db.session.get(Notificacion, act.notificacion_id)
    assert noti_vieja is not None and noti_vieja.deleted_at is not None
    assert noti_nueva is not None and noti_nueva.deleted_at is None
    assert noti_nueva.numero_acta == acta_nueva


def test_reactivar_comprobacion_misma_acta(app_ctx) -> None:
    act, _rub, _doc = _mk_actuacion_base()
    acta_num = _ot_num()
    aplicar_payload_actuacion(
        act,
        {"comprobacion": {"acta_num": acta_num, "motivo": "Motivo test"}},
    )
    db.session.commit()
    cid = act.comprobacion_id
    assert cid is not None

    quitar_acta_canal_actas(act.id, "COMPROBACION")
    comp = db.session.get(Comprobacion, cid)
    assert comp is not None and comp.deleted_at is not None

    aplicar_payload_actuacion(
        act,
        {"comprobacion": {"acta_num": acta_num, "motivo": "Motivo test"}},
    )
    db.session.commit()
    db.session.refresh(act)
    db.session.refresh(comp)
    assert act.comprobacion_id == cid
    assert comp.deleted_at is None


def test_reactivar_inspeccion_misma_acta(app_ctx) -> None:
    act, _rub, _doc = _mk_actuacion_base()
    acta_num = _ot_num()
    attach_inspeccion(act, acta_num, crear=False)
    db.session.commit()
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None

    quitar_acta_canal_actas(act.id, "INSPECCION")
    assert Inspeccion.query.filter_by(actuacion_id=act.id).first() is None

    attach_inspeccion(act, acta_num, crear=False)
    db.session.commit()
    ins2 = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins2 is not None
    assert ins2.numero_acta == acta_num
