"""HOTFIX QA — Reinspección por Notificación: notificación origen + reencolado."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.presenters.completar_trabajo_presenters import (
    ruta_item_completar_trabajo_to_row,
)
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
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
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

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _mk_iniciador_reinspeccion_notificacion,
    _setup_borrador_con_iniciador,
    _unique_num,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_ot() -> str:
    return uuid4().hex[:6].upper()


def _mk_reinspeccion_notificacion_item_sin_notif_en_acta() -> tuple[
    RutaItem, Actuaciones, IniciadorRuta, User, Notificacion
]:
    """Actuación de trabajo sin notificacion_id (caso típico al abrir Completar trabajo)."""
    u = User(
        username=f"u_qa_{_unique_ot()}",
        email=f"qa_{_unique_ot()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()

    dom = Domicilio(calle=f"QaNot{_unique_ot()}", numero="1")
    db.session.add(dom)
    db.session.flush()

    vencida = date(2000, 1, 1) + timedelta(days=int(uuid4().hex[:6], 16) % 3650)
    noti = Notificacion(
        numero_acta=_unique_ot(),
        anio=2026,
        mes=6,
        fecha_vencimiento=vencida,
    )
    db.session.add(noti)
    db.session.flush()

    ot_base = OrdenTrabajo(numero_acta=_unique_ot(), anio=2026, mes=6)
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

    ot_work = OrdenTrabajo(numero_acta=_unique_ot(), anio=2026, mes=6)
    db.session.add(ot_work)
    db.session.flush()

    fecha_ruta = _fecha_ruta_aislada_mismo_anio(2026)
    act_work = Actuaciones(
        fecha=fecha_ruta,
        mes=fecha_ruta.month,
        anio=fecha_ruta.year,
        tipo="REINSPECCION",
        orden_trabajo_id=ot_work.id,
        domicilio_id=dom.id,
    )
    db.session.add(act_work)
    db.session.flush()

    ruta = RutaTrabajo(
        fecha=fecha_ruta,
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=u.id,
        numero=int(uuid4().hex[:4], 16) % 31_999 + 2,
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


def test_presenter_muestra_notificacion_origen_desde_iniciador(app_ctx) -> None:
    item, _act, _ini, _u, noti = _mk_reinspeccion_notificacion_item_sin_notif_en_acta()
    row = ruta_item_completar_trabajo_to_row(item)
    assert row["acta_notificacion_num"] == noti.numero_acta
    assert row["notificacion_origen_id"] == noti.id
    assert row["notificacion_origen_anio"] == 2026
    assert row["notificacion_origen_texto"] == f"{noti.numero_acta}/2026"


def test_presenter_respeta_acta_en_actuacion_si_existe(app_ctx) -> None:
    item, act, ini, _u, noti = _mk_reinspeccion_notificacion_item_sin_notif_en_acta()
    act.notificacion_id = noti.id
    db.session.commit()
    row = ruta_item_completar_trabajo_to_row(item)
    assert row["acta_notificacion_num"] == noti.numero_acta


@pytest.mark.parametrize("contra", ["LOCAL CERRADO", "CLIMA", "OTROS"])
def test_cierre_no_realizado_reencola_y_vuelve_a_pendientes(app_ctx, contra: str) -> None:
    item, _act, ini, u, noti = _mk_reinspeccion_notificacion_item_sin_notif_en_acta()
    act_base_id = ini.actuacion_id

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": contra, "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    item_db = RutaItem.query.get(item.id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert item_db is not None
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"

    pendientes = list_reinspeccion_notificacion_operativas()
    assert act_base_id in {a.id for a in pendientes}
    assert any(a.notificacion_id == noti.id for a in pendientes)

    planif_ids = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini.id in planif_ids


def test_reintento_publica_con_ot_libre_tras_local_cerrado(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item1_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=u.id,
    )

    db.session.expire_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)
    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None and item2_db.actuacion_id is not None


def test_cierre_realizado_no_reencola(app_ctx) -> None:
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item_sin_notif_en_acta()
    act_base_id = ini.actuacion_id

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"tipo_actuacion": "REINSPECCION", "acta_inspeccion_num": _unique_ot()}
        ),
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"

    pendientes = list_reinspeccion_notificacion_operativas()
    assert act_base_id not in {a.id for a in pendientes}
    assert ini.id not in {row.id for row in planificable_iniciadores_base_query().all()}

    act_db = Actuaciones.query.get(act.id)
    assert act_db is not None and act_db.notificacion_id == noti.id


def test_no_duplica_iniciadores_activos_misma_notificacion(app_ctx) -> None:
    item, _act, ini, u, noti = _mk_reinspeccion_notificacion_item_sin_notif_en_acta()
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()
    activos = (
        IniciadorRuta.query.filter(
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.notificacion_id == noti.id,
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(("CUMPLIDO", "CERRADO_NO_EXISTE_LOCAL")),
        )
        .all()
    )
    assert len(activos) == 1
    assert activos[0].id == ini.id
