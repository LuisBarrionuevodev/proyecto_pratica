"""PR11.1 — Publicar ruta: validación OT sin falsos positivos en reinspección por notificación."""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    buscar_conflicto_orden_trabajo_al_publicar,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import RutaPublicarDebugError
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _fecha_ruta_aislada_mismo_anio(anio: int = 2026) -> date:
    """Día único dentro del año de la OT (mantiene resolución anio) evitando uq fecha+turno+numero."""
    return date(anio, 1, 1) + timedelta(days=random.randint(0, 364))


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    u = User(
        username=f"u_pr111_{_unique_num()}",
        email=f"pr111_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _dos_inspectores() -> tuple[Inspector, Inspector]:
    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return rows[0], rows[1]


def _mk_iniciador_reinspeccion_notificacion() -> tuple[IniciadorRuta, Actuaciones, Notificacion, User]:
    u = _mk_user()
    dom = Domicilio(calle=f"Pr111_{_unique_num()}", numero="1")
    db.session.add(dom)
    db.session.flush()

    noti = Notificacion(
        numero_acta=_unique_num(),
        anio=2026,
        mes=6,
        fecha_vencimiento=date.today() - timedelta(days=2),
    )
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
        estado_iniciador="PENDIENTE",
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
    db.session.commit()
    return ini, act_base, noti, u


def _setup_borrador_con_iniciador(
    ini: IniciadorRuta,
    *,
    numero_ot: str | None = None,
    fecha_ruta: date | None = None,
) -> tuple[RutaTrabajo, RutaItem]:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ins1, ins2 = _dos_inspectores()
    f = fecha_ruta or date(2026, 7, 21)
    ruta = RutaTrabajo(
        fecha=f,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR11.1", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    ot_num = numero_ot or _unique_num()
    for item in items:
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=ot_num,
        )
    item = (
        RutaItem.query.filter(
            RutaItem.ruta_trabajo_id == ruta.id,
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    assert item is not None
    db.session.commit()
    return ruta, item


def _publicar_y_cerrar_no_realizado(
    ruta: RutaTrabajo,
    item: RutaItem,
    user_id: int,
    *,
    contra: str = "LOCAL CERRADO",
) -> Actuaciones:
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None and item_db.actuacion_id is not None
    act_id = item_db.actuacion_id
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_db.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": contra, "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expire_all()
    act = Actuaciones.query.get(act_id)
    assert act is not None
    ini = IniciadorRuta.query.get(item_db.iniciador_ruta_id)
    assert ini is not None and ini.estado_iniciador == "PENDIENTE"
    return act


def test_pr11_1_reinspeccion_notificacion_publica_con_ot_nueva(app_ctx) -> None:
    ini, _act_base, _noti, _u = _mk_iniciador_reinspeccion_notificacion()
    ruta, item = _setup_borrador_con_iniciador(ini)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None
    assert item_db.actuacion_id is not None
    act = Actuaciones.query.get(item_db.actuacion_id)
    assert act is not None
    assert act.tipo == "REINSPECCION"
    assert act.notificacion_id == ini.notificacion_id


def test_pr11_1_reencolado_no_realizado_republica_sin_falso_409_misma_ot(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=fecha)
    act_prev = _publicar_y_cerrar_no_realizado(ruta1, item1, u.id)

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_prev.id
    act_prev_db = Actuaciones.query.get(act_prev.id)
    assert act_prev_db is not None
    assert act_prev_db.orden_trabajo_id == item2_db.orden_trabajo_id


def test_pr11_1_reencolado_no_realizado_republica_con_ot_distinta(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=_unique_num(), fecha_ruta=fecha)
    act_prev = _publicar_y_cerrar_no_realizado(ruta1, item1, u.id)

    nueva_ot = _unique_num()
    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=nueva_ot, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    act_prev_db = Actuaciones.query.get(act_prev.id)
    assert item2_db is not None and act_prev_db is not None
    assert item2_db.actuacion_id == act_prev_db.id
    ot = OrdenTrabajo.query.filter_by(numero_acta=nueva_ot, anio=2026).first()
    assert ot is not None
    assert act_prev_db.orden_trabajo_id == ot.id


def test_pr11_1_ot_en_actuacion_activa_en_proceso_bloquea(app_ctx) -> None:
    ini, _act_base, _noti, _u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None

    ini2, _, _, _ = _mk_iniciador_reinspeccion_notificacion()
    ruta2, item2 = _setup_borrador_con_iniciador(ini2, numero_ot=_unique_num())
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    item2_db.orden_trabajo_id = item1_db.orden_trabajo_id
    db.session.commit()

    with pytest.raises(RuntimeError, match="actuación"):
        publicar_ruta_trabajo(ruta_id=ruta2.id)


def test_pr11_1_item_no_realizado_no_genera_conflicto_ot(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    act_prev = _publicar_y_cerrar_no_realizado(ruta1, item1, u.id)

    conflicto = buscar_conflicto_orden_trabajo_al_publicar(
        orden_trabajo_id=act_prev.orden_trabajo_id,
        ruta_item_id=999_999,
        iniciador_ruta_id=ini.id,
    )
    assert conflicto is None


def test_pr11_1_actuacion_base_inspeccion_bloquea_misma_ot(app_ctx) -> None:
    ini, act_base, _noti, _u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = act_base.orden_trabajo.numero_acta
    assert ot_num is not None

    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=_fecha_ruta_aislada_mismo_anio(2026),
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre="Grupo PR11.1", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=[ins1.id, ins2.id],
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini.id],
    )
    item = items[0]
    with pytest.raises(RutaPublicarDebugError, match="actuación"):
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=ot_num,
        )
