"""PR11.1f — IntegrityError orden_trabajo_id: resolver ignorado / UPDATE vs ocupante."""

from __future__ import annotations

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
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
    resolver_actuacion_para_publicar_item,
)
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import RutaPublicarDebugError
from app.models import Actuaciones, IniciadorRuta, Inspector, OrdenTrabajo, Rubro, RutaItem, User

from tests.test_ruta_publicar_integrity_reintento_pr11_1e import (
    _insertar_segunda_actuacion_legacy_dual,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _setup_borrador_con_iniciador,
    _unique_num,
)
from tests.test_ruta_publicar_orden_trabajo_pr11_1b import _mk_iniciador_relevamiento


def _fecha_fixture_aislada() -> date:
    """Día aislado para evitar colisiones en BD compartida."""
    n = int(uuid4().hex[:8], 16) % 3650
    return date(2090, 1, 1) + timedelta(days=n)


def _count_actuaciones_iniciador(ini_id: int) -> int:
    """Cuenta actuaciones vinculadas al iniciador vía ítems de ruta (no total global)."""
    return (
        db.session.query(Actuaciones)
        .join(RutaItem, RutaItem.actuacion_id == Actuaciones.id)
        .filter(RutaItem.iniciador_ruta_id == ini_id, RutaItem.deleted_at.is_(None))
        .distinct()
        .count()
    )


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


def _assert_ot_consumida_por_otro_flujo(
    exc: RutaPublicarDebugError,
    *,
    ot_num: str | None = None,
) -> None:
    debug = exc.debug
    assert debug.get("validator") == "orden_trabajo_ocupada_por_otro_flujo"
    assert "ya fue utilizada en otra actuación" in str(exc)
    assert "esa OT queda consumida" in str(exc)
    assert "Seleccione una orden de trabajo libre" in str(exc)
    assert debug.get("actuacion_ocupante_id") is not None
    assert debug.get("iniciador_ocupante_id") is not None
    assert debug.get("actuacion_ocupante_tipo") is not None
    if ot_num is not None:
        assert debug.get("numero_orden_trabajo") == ot_num


def _asignar_ot_consumida_a_item(item_id: int, ot_id: int) -> None:
    item_db = RutaItem.query.get(item_id)
    assert item_db is not None
    item_db.orden_trabajo_id = ot_id
    db.session.commit()


def test_pr11_1f_dos_actuaciones_mismo_iniciador_prefiere_ocupante_ot_objetivo(app_ctx) -> None:
    """
    Estado legacy: dos actuaciones del mismo iniciador con OT distintas.
    Al republicar con OT del segundo intento, debe reutilizar act2 (ya tiene esa OT)
    y no actualizar act1 (evita IntegrityError ix_orden_trabajo_id).
    """
    rub = Rubro.query.first()
    ins = Inspector.query.first()
    assert rub and ins
    u = User(
        username=f"u_pr11f_{uuid4().hex[:8]}",
        email=f"pr11f_{uuid4().hex[:8]}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()

    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-10",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": f"Pr11f_{uuid4().hex[:6]}", "numero": "1"},
            "rubro_nombre": rub.nombre,
        }
    )
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id).first()
    assert ini is not None
    db.session.commit()

    hoy = _fecha_fixture_aislada()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    act1_id = int(item1_db.actuacion_id)
    ot1_id = int(item1_db.orden_trabajo_id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    act2_id, ot2_id = _insertar_segunda_actuacion_legacy_dual(
        ini=ini,
        act1_id=act1_id,
        ot1_id=ot1_id,
        ot2_num=ot2,
        hoy=hoy,
        user_id=u.id,
    )
    assert act2_id != act1_id

    resolved = resolver_actuacion_para_publicar_item(
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot2_id,
    )
    assert resolved is not None
    assert resolved.id == act2_id

    count_ini_antes = _count_actuaciones_iniciador(ini.id)
    ruta3, item3 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta3.id)
    db.session.expire_all()

    item3_db = RutaItem.query.get(item3.id)
    assert item3_db is not None
    assert item3_db.actuacion_id == act2_id
    assert _count_actuaciones_iniciador(ini.id) == count_ini_antes
    assert Actuaciones.query.filter(Actuaciones.orden_trabajo_id == ot2_id).count() == 1


def test_pr11_1f_republicar_misma_ot_no_crea_segunda_actuacion_local_cerrado(app_ctx) -> None:
    """Caso QA: actuación previa con OT objetivo + LOCAL CERRADO → reutilizar, no INSERT."""
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    hoy = _fecha_fixture_aislada()
    ot_num = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    act_id = int(item1_db.actuacion_id)
    ot_id = int(item1_db.orden_trabajo_id)
    _cerrar_local_cerrado(item1_db.id, u.id)
    db.session.expire_all()

    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"

    count_ini_antes = _count_actuaciones_iniciador(ini.id)
    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta2.id)
    db.session.expire_all()

    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_id
    assert _count_actuaciones_iniciador(ini.id) == count_ini_antes
    assert Actuaciones.query.filter(Actuaciones.orden_trabajo_id == ot_id).count() == 1


def test_pr11_1f_ot_ocupada_por_otro_iniciador_409_explicito_no_integrity(app_ctx) -> None:
    """OT de otro flujo → 409 claro al publicar, no IntegrityError en commit."""
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = _fecha_fixture_aislada()
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    assert item_a_db is not None
    ot_id = int(item_a_db.orden_trabajo_id)

    ruta_b, item_b = _setup_borrador_con_iniciador(
        ini_b, numero_ot=_unique_num(), fecha_ruta=hoy
    )
    _asignar_ot_consumida_a_item(item_b.id, ot_id)

    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_por_otro_flujo(exc_info.value, ot_num=ot_num)


def test_pr11_1f_ot_consumida_otro_iniciador_local_cerrado_bloquea(app_ctx) -> None:
    """OT usada por otro iniciador con LOCAL CERRADO queda consumida → 409 claro."""
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = _fecha_fixture_aislada()
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    _cerrar_local_cerrado(item_a_db.id, u.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    assert item_a_db is not None
    assert item_a_db.estado_ejecucion == "NO_REALIZADO"
    ot_id = int(item_a_db.orden_trabajo_id)

    ruta_b, item_b = _setup_borrador_con_iniciador(
        ini_b, numero_ot=_unique_num(), fecha_ruta=hoy
    )
    _asignar_ot_consumida_a_item(item_b.id, ot_id)

    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_por_otro_flujo(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("actuacion_ocupante_contraproducencia") == "LOCAL CERRADO"
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1f_ot_consumida_otro_iniciador_no_realizado_bloquea(app_ctx) -> None:
    """OT usada por otro iniciador con NO_REALIZADO (CLIMA) queda consumida → 409 claro."""
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = _fecha_fixture_aislada()
    ot_num = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_num, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    _cerrar_no_realizado_clima(item_a_db.id, u.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    assert item_a_db is not None
    assert item_a_db.estado_ejecucion == "NO_REALIZADO"
    ot_id = int(item_a_db.orden_trabajo_id)

    ruta_b, item_b = _setup_borrador_con_iniciador(
        ini_b, numero_ot=_unique_num(), fecha_ruta=hoy
    )
    _asignar_ot_consumida_a_item(item_b.id, ot_id)

    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_b.id)

    _assert_ot_consumida_por_otro_flujo(exc_info.value, ot_num=ot_num)
    assert exc_info.value.debug.get("estado_ejecucion_ocupante") == "NO_REALIZADO"


def test_pr11_1f_reintento_mismo_iniciador_ot_libre_publica_ok(app_ctx) -> None:
    """Reintento del mismo iniciador con OT libre publica correctamente."""
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    hoy = _fecha_fixture_aislada()
    ot1 = _unique_num()
    ot2 = _unique_num()
    while ot2 == ot1:
        ot2 = _unique_num()

    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=ot1, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    act_id = int(item1_db.actuacion_id)
    _cerrar_local_cerrado(item1_db.id, u.id)

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot2, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta2.id)
    db.session.expire_all()

    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_id
    ot2_row = OrdenTrabajo.query.filter_by(numero_acta=ot2, anio=hoy.year).first()
    assert ot2_row is not None
    act_db = Actuaciones.query.get(act_id)
    assert act_db is not None
    assert act_db.orden_trabajo_id == ot2_row.id


def test_pr11_1f_reintento_mismo_iniciador_ot_ocupada_por_otro_bloquea(app_ctx) -> None:
    """Reintento del mismo iniciador con OT ya consumida por otro flujo → 409 claro."""
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ini_a = _mk_iniciador_relevamiento()
    ini_b = _mk_iniciador_relevamiento()
    hoy = _fecha_fixture_aislada()
    ot_ocupada = _unique_num()
    ot_libre = _unique_num()
    while ot_libre == ot_ocupada:
        ot_libre = _unique_num()

    ruta_a, item_a = _setup_borrador_con_iniciador(ini_a, numero_ot=ot_ocupada, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_a.id)
    db.session.expire_all()
    item_a_db = RutaItem.query.get(item_a.id)
    _cerrar_local_cerrado(item_a_db.id, u.id)
    ot_id = int(item_a_db.orden_trabajo_id)

    ruta_b, item_b = _setup_borrador_con_iniciador(ini_b, numero_ot=ot_libre, fecha_ruta=hoy)
    publicar_ruta_trabajo(ruta_id=ruta_b.id)
    db.session.expire_all()
    item_b_db = RutaItem.query.get(item_b.id)
    _cerrar_local_cerrado(item_b_db.id, u.id)

    ruta_c, item_c = _setup_borrador_con_iniciador(ini_b, numero_ot=ot_libre, fecha_ruta=hoy)
    _asignar_ot_consumida_a_item(item_c.id, ot_id)

    with pytest.raises(RutaPublicarDebugError) as exc_info:
        publicar_ruta_trabajo(ruta_id=ruta_c.id)

    _assert_ot_consumida_por_otro_flujo(exc_info.value, ot_num=ot_ocupada)
    assert exc_info.value.debug.get("iniciador_id") == ini_b.id
