"""PR11.1c — Publicar ruta: reintento mismo día con OT distinta tras Local cerrado."""

from __future__ import annotations

import random
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.denuncias.services.denuncias_service import crear_denuncia_con_iniciador
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import (
    Actuaciones,
    IniciadorRuta,
    Inspector,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    User,
)

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _mk_iniciador_reinspeccion_notificacion,
    _mk_user,
    _publicar_y_cerrar_no_realizado,
    _setup_borrador_con_iniciador,
    _unique_num,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1b import (
    _mk_iniciador_denuncia,
    _mk_iniciador_relevamiento,
    _publicar_cerrar_reencolar,
)


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _fecha_mismo_dia() -> date:
    return date.today()


def _fecha_fixture_aislada() -> date:
    """Día aislado para evitar colisiones en BD compartida (ruta uq fecha+turno+numero, OT por año)."""
    return date(2099, 1, 1) + timedelta(days=random.randint(0, 360))


def _republicar_mismo_dia_ot_distinta(
    ini: IniciadorRuta,
    *,
    user_id: int,
    tipo_cierre: str = "INSPECCION",
) -> tuple[Actuaciones, OrdenTrabajo]:
    """Intento 1 con OT A + Local cerrado; intento 2 mismo día con OT B → publica OK."""
    fecha = _fecha_mismo_dia()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    act_prev = _publicar_cerrar_reencolar(
        ini,
        ot_num=ot1,
        user_id=user_id,
        tipo=tipo_cierre,
        fecha_ruta=fecha,
    )

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    act_db = Actuaciones.query.get(act_prev.id)
    ot_db = OrdenTrabajo.query.filter_by(numero_acta=ot2, anio=fecha.year).first()
    assert item2_db is not None and act_db is not None and ot_db is not None
    assert item2_db.actuacion_id == act_prev.id
    assert act_db.orden_trabajo_id == ot_db.id
    assert act_db.contraproducencia is None
    assert item2_db.ruta_trabajo.fecha == fecha
    return act_db, ot_db


def test_pr11_1c_relevamiento_mismo_dia_ot_distinta_local_cerrado(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    _republicar_mismo_dia_ot_distinta(ini, user_id=u.id, tipo_cierre="INSPECCION")


def test_pr11_1c_denuncia_mismo_dia_ot_distinta_local_cerrado(app_ctx) -> None:
    ini = _mk_iniciador_denuncia()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    _republicar_mismo_dia_ot_distinta(ini, user_id=u.id, tipo_cierre="INSPECCION")


def test_pr11_1c_reinspeccion_notificacion_mismo_dia_ot_distinta_local_cerrado(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    fecha = _fecha_mismo_dia()
    ot1, ot2 = _unique_num(), _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=fecha)
    act_prev = _publicar_y_cerrar_no_realizado(ruta1, item1, u.id, contra="LOCAL CERRADO")

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    act_db = Actuaciones.query.get(act_prev.id)
    ot_db = OrdenTrabajo.query.filter_by(numero_acta=ot2, anio=fecha.year).first()
    assert item2_db is not None and act_db is not None and ot_db is not None
    assert item2_db.actuacion_id == act_prev.id
    assert act_db.orden_trabajo_id == ot_db.id


def test_pr11_1c_mismo_dia_misma_ot_sigue_ok(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    fecha = _fecha_mismo_dia()
    ot_num = _unique_num()
    act_prev = _publicar_cerrar_reencolar(
        ini, ot_num=ot_num, user_id=u.id, fecha_ruta=fecha
    )
    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)
    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_prev.id


def test_pr11_1c_item_en_proceso_sigue_bloqueando_ot(app_ctx) -> None:
    ini1 = _mk_iniciador_relevamiento()
    fecha = _fecha_fixture_aislada()
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini1, numero_ot=ot_num, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None

    ini2 = _mk_iniciador_relevamiento()
    ruta2, item2 = _setup_borrador_con_iniciador(ini2, numero_ot=_unique_num(), fecha_ruta=fecha)
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    item2_db.orden_trabajo_id = item1_db.orden_trabajo_id
    db.session.commit()

    with pytest.raises(RuntimeError, match="actuación"):
        publicar_ruta_trabajo(ruta_id=ruta2.id)


def test_pr11_1c_realizada_previa_no_permite_reasignar(app_ctx) -> None:
    """Visita REALIZADA deja el iniciador CUMPLIDO: no puede reingresar a otra ruta."""
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    fecha = _fecha_mismo_dia()
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=_unique_num(), fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1 = RutaItem.query.get(item1.id)
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item1.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"tipo_actuacion": "INSPECCION"}
            ),
            ejecutado_por_user_id=u.id,
        )
    db.session.expire_all()
    ini_db = IniciadorRuta.query.get(ini.id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "CUMPLIDO"

    from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
    from app.domains.rutas_trabajo.services.grupo_inspectores_service import (
        replace_grupo_inspectores,
    )
    from app.models import RutaTrabajo
    from tests.test_ruta_publicar_orden_trabajo_pr11_1 import _dos_inspectores

    ins1, ins2 = _dos_inspectores()
    ruta2 = RutaTrabajo(
        fecha=fecha,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=random.randint(2, 32000),
        created_by_user_id=u.id,
    )
    db.session.add(ruta2)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta2.id, nombre="Grupo bloqueo", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta2.id, grupo_id=grupo.id, inspector_ids=[ins1.id, ins2.id]
    )
    with pytest.raises(RuntimeError, match="PENDIENTE"):
        assign_iniciadores_to_grupo(
            ruta_id=ruta2.id, grupo_id=grupo.id, iniciador_ids=[ini.id]
        )


def test_pr11_1c_legacy_estado_ruta_no_realizado_mismo_dia_nueva_ot(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    fecha = _fecha_mismo_dia()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    act_prev = _publicar_cerrar_reencolar(
        ini, ot_num=ot1, user_id=u.id, fecha_ruta=fecha
    )
    item_prev = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.actuacion_id == act_prev.id,
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    assert item_prev is not None
    item_prev.estado_ruta_item = "NO_REALIZADO"
    item_prev.estado_ejecucion = "NO_REALIZADO"
    db.session.commit()

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    act_db = Actuaciones.query.get(act_prev.id)
    assert item2_db is not None and act_db is not None
    assert item2_db.actuacion_id == act_prev.id


def test_pr11_1c_fallback_estado_ejecucion_no_realizado_sin_finalizar_item(app_ctx) -> None:
    """Ítem con estado_ejecucion=NO_REALIZADO aunque estado_ruta_item no sea FINALIZADO."""
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    fecha = _fecha_mismo_dia()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    act_prev = _publicar_cerrar_reencolar(
        ini, ot_num=ot1, user_id=u.id, fecha_ruta=fecha
    )
    item_prev = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.actuacion_id == act_prev.id,
        )
        .first()
    )
    assert item_prev is not None
    item_prev.estado_ruta_item = "EN_PROCESO"
    item_prev.estado_ejecucion = "NO_REALIZADO"
    db.session.commit()

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_prev.id
