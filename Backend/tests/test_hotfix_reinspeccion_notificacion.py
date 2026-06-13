"""HOTFIX-CIERRE-DIA: reinspección notificación sale de pendientes al completar."""

from __future__ import annotations

import random
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    list_reinspeccion_notificacion_operativas,
)
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"u_hotfix_{_unique_num()}",
        email=f"hotfix_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_reinspeccion_notificacion_item() -> tuple[RutaItem, Actuaciones, IniciadorRuta, User, Notificacion]:
    u = _mk_user()
    dom = Domicilio(calle=f"HotfixNot{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()

    vencida = date.today() - timedelta(days=3)
    noti = Notificacion(numero_acta=_unique_num(), anio=2026, mes=6, fecha_vencimiento=vencida)
    db.session.add(noti)
    db.session.flush()

    ot_base = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot_base)
    db.session.flush()

    act_base = Actuaciones(
        fecha=date(2026, 5, 1),
        mes=5,
        anio=2026,
        tipo="INSPECCION",
        notificacion_id=noti.id,
        domicilio_id=dom.id,
        orden_trabajo_id=ot_base.id,
    )
    db.session.add(act_base)
    db.session.flush()

    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_NOTIFICACION",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 6, 1),
        anio=2026,
        mes=6,
        domicilio_id=dom.id,
        notificacion_id=noti.id,
        actuacion_id=act_base.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
    db.session.flush()

    ot_work = OrdenTrabajo(numero_acta=_unique_num(), anio=2026, mes=6)
    db.session.add(ot_work)
    db.session.flush()

    act_work = Actuaciones(
        fecha=date(2026, 6, 10),
        mes=6,
        anio=2026,
        tipo="REINSPECCION",
        orden_trabajo_id=ot_work.id,
        domicilio_id=dom.id,
    )
    db.session.add(act_work)
    db.session.flush()

    ruta = RutaTrabajo(
        fecha=date(2026, 6, 10),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta)
    db.session.flush()

    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot_work.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act_work.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.flush()
    db.session.commit()
    return item, act_work, ini, u, noti


def test_pendiente_reinspeccion_aparece_si_estado_pendiente(app_ctx) -> None:
    _item, _act, ini, _u, _noti = _mk_reinspeccion_notificacion_item()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    ini_db.estado_iniciador = "PENDIENTE"
    db.session.commit()

    pendientes = list_reinspeccion_notificacion_operativas()
    act_ids = {a.id for a in pendientes}
    assert ini.actuacion_id in act_ids


def test_cierre_realizada_saca_de_pendientes_y_vincula_notificacion(app_ctx) -> None:
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "REINSPECCION",
            "acta_inspeccion_num": _unique_num(),
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    act_db = Actuaciones.query.get(act.id)
    item_db = RutaItem.query.get(item.id)

    assert ini_db is not None
    assert ini_db.estado_iniciador == "CUMPLIDO"
    assert act_db is not None
    assert act_db.notificacion_id == noti.id
    assert act_db.tipo == "REINSPECCION"
    assert item_db is not None
    assert item_db.estado_ruta_item == "FINALIZADO"
    assert item_db.estado_ejecucion == "REALIZADO"

    pendientes = list_reinspeccion_notificacion_operativas()
    act_ids = {a.id for a in pendientes}
    assert ini.actuacion_id not in act_ids

    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id not in planif_ids


def test_iniciador_cumplido_no_aparece_en_planificable(app_ctx) -> None:
    item, act, ini, u, _noti = _mk_reinspeccion_notificacion_item()
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"tipo_actuacion": "REINSPECCION", "acta_inspeccion_num": _unique_num()}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    assert IniciadorRuta.query.get(ini.id).estado_iniciador == "CUMPLIDO"
    q = planificable_iniciadores_base_query().filter(IniciadorRuta.id == ini.id).all()
    assert q == []
