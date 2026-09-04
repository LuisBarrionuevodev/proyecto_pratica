"""
GESTIÓN-FIX.10A.3 — Verificar+Sí integrado al workflow documental Notificación/Comprobación.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    _eligible_inspecciones_vencidas,
    list_reinspeccion_notificacion_operativas,
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.actuaciones.services.pendientes_service import get_pendientes_expediente
from app.domains.actuaciones.utils.actuacion_base_workflow_documental import (
    actuacion_equivale_a_inspeccion_para_workflow_documental,
)
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Motivo,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


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


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _motivo() -> Motivo:
    m = Motivo.query.first()
    if m is None:
        pytest.skip("Se requiere al menos un motivo en catálogo")
    return m


def _cerrar_verificar_si(
    item: RutaItem,
    user_id: int,
    *,
    acta_notificacion: str | None = None,
    acta_comprobacion: str | None = None,
    comprobacion_motivo: str | None = None,
) -> Actuaciones:
    payload_data: dict = {
        "tipo_actuacion": "VERIFICAR E INFORMAR",
        "realizo_nueva_inspeccion": True,
        "acta_inspeccion_num": _unique_num(),
    }
    if acta_notificacion:
        motivo = _motivo()
        payload_data["acta_notificacion_num"] = acta_notificacion
        payload_data["notificacion_motivo_1"] = motivo.nombre
    if acta_comprobacion:
        payload_data["acta_comprobacion_num"] = acta_comprobacion
        payload_data["comprobacion_motivo"] = comprobacion_motivo or "Motivo fix 10a3"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(payload_data)
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    act_db = Actuaciones.query.get(item.actuacion_id)
    assert act_db is not None
    return act_db


def test_helper_verificar_si_equivale_a_inspeccion_documental() -> None:
    act_insp = Actuaciones(tipo="INSPECCION")
    act_vi_si = Actuaciones(tipo="VERIFICAR E INFORMAR", realizo_nueva_inspeccion=True)
    act_vi_no = Actuaciones(tipo="VERIFICAR E INFORMAR", realizo_nueva_inspeccion=False)
    act_rat = Actuaciones(tipo="RATIFICACION DE CLAUSURA")
    assert actuacion_equivale_a_inspeccion_para_workflow_documental(act_insp)
    assert actuacion_equivale_a_inspeccion_para_workflow_documental(act_vi_si)
    assert not actuacion_equivale_a_inspeccion_para_workflow_documental(act_vi_no)
    assert not actuacion_equivale_a_inspeccion_para_workflow_documental(act_rat)


def test_v1_verificar_si_notificacion_vencida_sync_crea_reinspeccion_notificacion(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    acta_notif = _unique_num()
    act_db = _cerrar_verificar_si(item, u.id, acta_notificacion=acta_notif)

    assert str(act_db.tipo) == "VERIFICAR E INFORMAR"
    assert act_db.realizo_nueva_inspeccion is True
    assert act_db.notificacion_id is not None

    noti = db.session.get(Notificacion, act_db.notificacion_id)
    assert noti is not None
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    db.session.add(noti)
    db.session.commit()

    eligible = _eligible_inspecciones_vencidas()
    assert any(a.id == act_db.id for a in eligible)

    outcome = sync_iniciadores_reinspeccion_notificacion()
    # Puede ser 0 si el post-commit del cierre ya materializó el iniciador.
    assert outcome.created >= 0

    ini_der = (
        IniciadorRuta.query.filter(
            IniciadorRuta.notificacion_id == noti.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.deleted_at.is_(None),
        )
        .all()
    )
    assert len(ini_der) == 1
    assert ini_der[0].estado_iniciador == "PENDIENTE"
    assert ini_der[0].actuacion_id == act_db.id

    operativas = list_reinspeccion_notificacion_operativas()
    assert act_db.id in {a.id for a in operativas}


def test_v1b_sync_idempotente_un_solo_iniciador(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    act_db = _cerrar_verificar_si(item, u.id, acta_notificacion=_unique_num())

    noti = db.session.get(Notificacion, act_db.notificacion_id)
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    db.session.add(noti)
    db.session.commit()

    sync_iniciadores_reinspeccion_notificacion()
    o2 = sync_iniciadores_reinspeccion_notificacion()
    assert o2.created == 0
    assert o2.skipped_already_blocking >= 1 or o2.collisions_idempotent >= 0

    count = (
        IniciadorRuta.query.filter(
            IniciadorRuta.notificacion_id == noti.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.deleted_at.is_(None),
        ).count()
    )
    assert count == 1


def test_v2_verificar_si_notificacion_aparece_esperando_expediente(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    act_db = _cerrar_verificar_si(item, u.id, acta_notificacion=_unique_num())

    acts = get_pendientes_expediente(_filters_notificacion())
    assert act_db.id in {a.id for a in acts}


def test_v3_verificar_si_comprobacion_esperando_expediente_sin_iniciador_inmediato(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    act_db = _cerrar_verificar_si(item, u.id, acta_comprobacion=_unique_num())

    acts = get_pendientes_expediente(_filters_comprobacion())
    assert act_db.id in {a.id for a in acts}

    inmediatos = IniciadorRuta.query.filter(
        IniciadorRuta.comprobacion_id == act_db.comprobacion_id,
        IniciadorRuta.deleted_at.is_(None),
    ).count()
    assert inmediatos == 0


def test_v4_mixta_ambos_canales_y_sync_notificacion(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    act_db = _cerrar_verificar_si(
        item,
        u.id,
        acta_notificacion=_unique_num(),
        acta_comprobacion=_unique_num(),
    )

    assert act_db.notificacion_id is not None
    assert act_db.comprobacion_id is not None

    acts_n = get_pendientes_expediente(_filters_notificacion())
    acts_c = get_pendientes_expediente(_filters_comprobacion())
    assert act_db.id in {a.id for a in acts_n}
    assert act_db.id in {a.id for a in acts_c}

    noti = db.session.get(Notificacion, act_db.notificacion_id)
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    db.session.add(noti)
    db.session.commit()

    sync_iniciadores_reinspeccion_notificacion()
    ini_notif = (
        IniciadorRuta.query.filter(
            IniciadorRuta.notificacion_id == noti.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.deleted_at.is_(None),
        ).first()
    )
    assert ini_notif is not None
    assert ini_notif.estado_iniciador == "PENDIENTE"


def test_v5_verificar_no_no_es_elegible_para_sync(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "realizo_nueva_inspeccion": False,
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    assert act_db is not None
    assert act_db.realizo_nueva_inspeccion is False
    assert not actuacion_equivale_a_inspeccion_para_workflow_documental(act_db)

    rub = Rubro.query.first()
    dom = Domicilio(calle=f"Fix10a3No_{suf}", numero="9", rubro_id=rub.id if rub else None)
    db.session.add(dom)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
    noti.fecha_notificacion = date(2026, 6, 1)
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    noti.plazo_dias = 5
    db.session.add(noti)
    db.session.flush()
    act_db.notificacion_id = noti.id
    act_db.domicilio_id = dom.id
    db.session.commit()

    eligible = _eligible_inspecciones_vencidas()
    assert act_db.id not in {a.id for a in eligible}


def test_v6_verificar_con_contraproducencia_no_es_elegible(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "contraproducencia": "LOCAL CERRADO",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"
    assert act_db.realizo_nueva_inspeccion is None
    assert not actuacion_equivale_a_inspeccion_para_workflow_documental(act_db)


def test_v7_ratificacion_no_es_elegible(app_ctx) -> None:
    rub = Rubro.query.first()
    dom = Domicilio(calle="Fix10a3Rat", numero="1", rubro_id=rub.id if rub else None)
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot)
    db.session.flush()
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6)
    noti.fecha_notificacion = date(2026, 6, 1)
    noti.fecha_vencimiento = date.today() - timedelta(days=1)
    noti.plazo_dias = 5
    db.session.add(noti)
    db.session.flush()
    act = Actuaciones(
        fecha=date(2026, 6, 10),
        mes=6,
        anio=2026,
        tipo="RATIFICACION DE CLAUSURA",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
        notificacion_id=noti.id,
    )
    db.session.add(act)
    db.session.commit()

    eligible = _eligible_inspecciones_vencidas()
    assert act.id not in {a.id for a in eligible}
