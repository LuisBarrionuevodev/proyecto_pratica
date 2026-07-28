"""PR11.1g — PATCH orden-trabajo: validar OT consumida al asignar en card."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import RutaPublicarDebugError
from app.models import RutaItem, User

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _setup_borrador_con_iniciador,
    _unique_num,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1b import _mk_iniciador_relevamiento


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _cerrar_local_cerrado(item_id: int, user_id: int) -> None:
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
            ),
            ejecutado_por_user_id=user_id,
        )


def _cerrar_no_realizado_clima(item_id: int, user_id: int) -> None:
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": "CLIMA", "tipo_actuacion": "INSPECCION"}
            ),
            ejecutado_por_user_id=user_id,
        )


def _assert_ot_consumida_409(exc: RutaPublicarDebugError, *, ot_num: str | None = None) -> None:
    assert exc.debug.get("validator") == "orden_trabajo_ocupada_por_otro_flujo"
    assert "ya fue utilizada en otra actuación" in str(exc)
    assert "esa OT queda consumida" in str(exc)
    assert exc.debug.get("actuacion_ocupante_id") is not None
    assert exc.debug.get("iniciador_ocupante_id") is not None
    if ot_num is not None:
        assert exc.debug.get("numero_orden_trabajo") == ot_num


def test_pr11_1g_patch_ot_libre_asigna_ok(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot_num = _unique_num()
    ruta, item = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    updated = set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=ot_num,
    )
    assert updated.orden_trabajo_id is not None
    assert updated.orden_trabajo.numero_acta == ot_num


def test_pr11_1g_patch_ot_otro_iniciador_en_proceso_bloquea(app_ctx) -> None:
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    assert item_a_db is not None
    ot_id = int(item_a_db.orden_trabajo_id)

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, numero_ot=_unique_num(), fecha_ruta=fecha)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        set_orden_trabajo_on_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    item_b_db = RutaItem.query.get(item_b.id)
    assert item_b_db is not None
    assert item_b_db.orden_trabajo_id != ot_id


def test_pr11_1g_patch_ot_otro_iniciador_local_cerrado_bloquea(app_ctx) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    _cerrar_local_cerrado(item_a_db.id, u.id)

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, numero_ot=_unique_num(), fecha_ruta=hoy)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        set_orden_trabajo_on_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("actuacion_ocupante_contraproducencia") == "LOCAL CERRADO"
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1g_patch_ot_otro_iniciador_no_realizado_clima_bloquea(app_ctx) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    _cerrar_no_realizado_clima(item_a_db.id, u.id)

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, numero_ot=_unique_num(), fecha_ruta=hoy)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        set_orden_trabajo_on_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1g_patch_ot_mismo_iniciador_reintento_permite(app_ctx) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot_num = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    updated = set_orden_trabajo_on_item(
        ruta_id=ruta2.id,
        item_id=item2.id,
        numero_orden_trabajo=ot_num,
    )
    assert updated.orden_trabajo_id is not None
    assert updated.orden_trabajo.numero_acta == ot_num


def test_pr11_1g_patch_ot_mismo_iniciador_ot_libre_permite(app_ctx) -> None:
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=hoy)
    updated = set_orden_trabajo_on_item(
        ruta_id=ruta2.id,
        item_id=item2.id,
        numero_orden_trabajo=ot2,
    )
    assert updated.orden_trabajo.numero_acta == ot2


def test_pr11_1g_patch_item_soft_deleted_no_bloquea_ot(app_ctx) -> None:
    """Ítem soft-deleted del mismo iniciador no debe bloquear reasignar la OT en borrador."""
    from datetime import datetime

    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini = _mk_iniciador_relevamiento()
    hoy = date.today()
    ot_num = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    _cerrar_local_cerrado(item1_db.id, u.id)
    item1_db.deleted_at = datetime.utcnow()
    db.session.commit()

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=_unique_num(), fecha_ruta=hoy)
    updated = set_orden_trabajo_on_item(
        ruta_id=ruta2.id,
        item_id=item2.id,
        numero_orden_trabajo=ot_num,
    )
    assert updated.orden_trabajo.numero_acta == ot_num
