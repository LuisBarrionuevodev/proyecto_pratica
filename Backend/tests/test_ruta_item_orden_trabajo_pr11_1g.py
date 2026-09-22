"""PR11.1g — OT-AUTO: conflictos OT en publicación (manual PATCH deshabilitado)."""

from __future__ import annotations

from datetime import date, datetime
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
from app.models import OrdenTrabajo, RutaItem, User

from tests.helpers.ruta_ot_test import asignar_ot_legacy_en_item
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _fecha_ruta_aislada_mismo_anio,
    _setup_borrador_con_iniciador,
    _unique_num,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1b import _mk_iniciador_relevamiento

_OT_AUTO_MSG = "numeración automática al publicar"


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


def test_pr11_1g_patch_manual_rechazado_ot_auto(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    ruta, item = _setup_borrador_con_iniciador(ini, fecha_ruta=date.today())
    with pytest.raises(RuntimeError, match=_OT_AUTO_MSG):
        set_orden_trabajo_on_item(
            ruta_id=ruta.id,
            item_id=item.id,
            numero_orden_trabajo=_unique_num(),
        )


def test_pr11_1g_publicar_ot_otro_iniciador_en_proceso_bloquea(app_ctx) -> None:
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    fecha = _fecha_ruta_aislada_mismo_anio(2026)
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=fecha)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    assert item_a_db is not None
    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, fecha_ruta=fecha)
    asignar_ot_legacy_en_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    item_b_db = RutaItem.query.get(item_b.id)
    assert item_b_db is not None
    assert item_b_db.actuacion_id is None
    ruta_b_db = db.session.get(type(ruta_b), ruta_b.id)
    assert ruta_b_db is not None
    assert ruta_b_db.estado_ruta == "BORRADOR"


def test_pr11_1g_publicar_ot_otro_iniciador_local_cerrado_bloquea(app_ctx) -> None:
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

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, fecha_ruta=hoy)
    asignar_ot_legacy_en_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("actuacion_ocupante_contraproducencia") == "LOCAL CERRADO"
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1g_publicar_ot_otro_iniciador_no_realizado_clima_bloquea(app_ctx) -> None:
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

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, fecha_ruta=hoy)
    asignar_ot_legacy_en_item(ruta_id=ruta_b.id, item_id=item_b.id, numero_orden_trabajo=ot_num)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1g_publicar_mismo_iniciador_reintento_rechaza_misma_ot_legacy(app_ctx) -> None:
    """Tras NO_REALIZADO, legacy OT histórica no puede reutilizarse al publicar."""
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

    ruta2, item2 = _setup_borrador_con_iniciador(ini, fecha_ruta=hoy)
    asignar_ot_legacy_en_item(ruta_id=ruta2.id, item_id=item2.id, numero_orden_trabajo=ot_num)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta2.id)
    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("iniciador_ocupante_id") == ini.id


def test_pr11_1g_publicar_mismo_iniciador_retry_ot_auto_nueva(app_ctx) -> None:
    """Retry sin legacy OT: publicación asigna OT automática distinta."""
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini = _mk_iniciador_relevamiento()
    hoy = date.today()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, fecha_ruta=hoy)
    _, _, meta1 = publicar_ruta_trabajo(ruta_id=ruta1.id)
    ot1 = meta1["ordenes_asignadas"][0]["numero_acta"]
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    ruta2, _item2 = _setup_borrador_con_iniciador(ini, fecha_ruta=hoy)
    _, _, meta2 = publicar_ruta_trabajo(ruta_id=ruta2.id)
    ot2 = meta2["ordenes_asignadas"][0]["numero_acta"]
    assert ot1 != ot2
    assert OrdenTrabajo.query.filter_by(numero_acta=ot1).count() >= 1


def test_pr11_1g_item_soft_deleted_sigue_bloqueando_ot_historica(app_ctx) -> None:
    """Soft-delete del ítem no libera la OT consumida por la actuación histórica."""
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

    ruta2, item2 = _setup_borrador_con_iniciador(ini, fecha_ruta=hoy)
    asignar_ot_legacy_en_item(ruta_id=ruta2.id, item_id=item2.id, numero_orden_trabajo=ot_num)
    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta2.id)
    _assert_ot_consumida_409(exc_info.value, ot_num=ot_num)

    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    item2_db.orden_trabajo_id = None
    db.session.commit()
    _, _, meta_ok = publicar_ruta_trabajo(ruta_id=ruta2.id)
    assert meta_ok["ordenes_asignadas"][0]["numero_acta"] != ot_num
