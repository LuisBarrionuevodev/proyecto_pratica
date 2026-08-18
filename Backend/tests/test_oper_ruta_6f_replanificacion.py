"""OPER-RUTA.6F — Replanificación tras contraproducencia / NO_REALIZADO reencolable."""

from __future__ import annotations

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
from app.domains.actuaciones.services.notificacion_estado_operativo_pool_service import (
    build_estado_operativo_pool_por_iniciador,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    iniciador_en_ruta_no_borrador_activa,
    ruta_item_bloquea_nueva_planificacion,
    validar_iniciador_elegible_para_pool,
)
from app.domains.rutas_trabajo.services.ruta_pool_dia_service import create_ruta_pool_dia_entry
from app.models import IniciadorRuta, RutaItem, RutaTrabajo, User
from tests.helpers.fixture_isolation import fecha_ruta_aislada_mismo_anio, unique_ot_numero, uniq_ruta_numero


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_user() -> User:
    suf = uuid4().hex[:8]
    u = User(
        username=f"op6f_{suf}",
        email=f"op6f_{suf}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _cerrar_local_cerrado(item_id: int, user_id: int, *, tipo: str = "INSPECCION") -> None:
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": tipo}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )


@pytest.mark.parametrize("contra", ["LOCAL CERRADO", "CLIMA"])
def test_relevamiento_reencolado_permite_pool_y_estado_pendiente(app_ctx, contra: str) -> None:
    from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada

    suf = uuid4().hex[:8]
    item_id, _act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"contraproducencia": contra, "tipo_actuacion": "INSPECCION"}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=payload,
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    ini = db.session.get(IniciadorRuta, ini_id)
    item = db.session.get(RutaItem, item_id)
    assert ini is not None and ini.estado_iniciador == "PENDIENTE"
    assert item is not None and item.estado_ruta_item == "FINALIZADO"
    assert item.estado_ejecucion == "NO_REALIZADO"
    assert iniciador_en_ruta_no_borrador_activa(int(ini.id)) is None
    assert ruta_item_bloquea_nueva_planificacion(item) is False

    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "pendiente"

    pool_fecha = fecha_ruta_aislada_mismo_anio(2098)
    row = create_ruta_pool_dia_entry(
        fecha=pool_fecha,
        turno_id=None,
        usuario_id=user_id,
        iniciador_ruta_id=int(ini.id),
    )
    assert row.estado == "EN_POOL"


def test_reinspeccion_oficio_reencolado_permite_pool(app_ctx) -> None:
    from tests.test_reinspeccion_oficio_reencolado import _mk_reinspeccion_oficio_en_ruta_publicada

    item, _act, ini, u, _ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    ini_id = int(ini.id)
    user_id = int(u.id)
    _cerrar_local_cerrado(item.id, user_id, tipo="VERIFICAR E INFORMAR")
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert iniciador_en_ruta_no_borrador_activa(ini_id) is None

    ctx = build_estado_operativo_pool_por_iniciador([ini_id])[ini_id]
    assert ctx["estado_operativo_pool"] == "pendiente"

    pool_fecha = fecha_ruta_aislada_mismo_anio(2097)
    row = create_ruta_pool_dia_entry(
        fecha=pool_fecha,
        turno_id=None,
        usuario_id=user_id,
        iniciador_ruta_id=ini_id,
    )
    assert row.estado == "EN_POOL"


def test_reinspeccion_notificacion_reencolado_permite_pool(app_ctx) -> None:
    from tests.test_notificacion_oper_ruta_3 import _mk_iniciador_reinspeccion, _mk_notif_act, _mk_user as mk_u3

    u = mk_u3()
    user_id = int(u.id)
    act, _ = _mk_notif_act(fecha=date(2026, 11, 1))
    ini = _mk_iniciador_reinspeccion(act, u)
    ini.estado_iniciador = "EN_EJECUCION"
    ruta = RutaTrabajo(
        fecha=date(2026, 11, 5),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=user_id,
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=user_id,
    )
    db.session.add(item)
    db.session.commit()
    ini_id = int(ini.id)

    _cerrar_local_cerrado(item.id, user_id, tipo="REINSPECCION")
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert iniciador_en_ruta_no_borrador_activa(ini_id) is None

    ctx = build_estado_operativo_pool_por_iniciador([ini_id])[ini_id]
    assert ctx["estado_operativo_pool"] == "pendiente"

    row = create_ruta_pool_dia_entry(
        fecha=fecha_ruta_aislada_mismo_anio(2096),
        turno_id=None,
        usuario_id=user_id,
        iniciador_ruta_id=ini_id,
    )
    assert row.estado == "EN_POOL"


def test_denuncia_reencolado_permite_pool(app_ctx) -> None:
    from app.models import Domicilio, OrdenTrabajo

    u = _mk_user()
    user_id = int(u.id)
    dom = Domicilio(calle=f"Den6f_{uuid4().hex[:6]}", numero="1")
    db.session.add(dom)
    db.session.flush()
    ot = OrdenTrabajo(numero_acta=unique_ot_numero(), anio=2026, mes=11)
    db.session.add(ot)
    db.session.flush()
    fo = date(2026, 11, 1)
    ini = IniciadorRuta(
        tipo_iniciador="DENUNCIA",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=fo,
        anio=fo.year,
        mes=fo.month,
        domicilio_id=dom.id,
        created_by_user_id=user_id,
    )
    db.session.add(ini)
    db.session.flush()
    from app.models import Actuaciones

    act = Actuaciones(
        fecha=fo,
        mes=fo.month,
        anio=fo.year,
        tipo="INSPECCION",
        orden_trabajo_id=ot.id,
        domicilio_id=dom.id,
    )
    db.session.add(act)
    db.session.flush()
    ruta = RutaTrabajo(
        fecha=fo,
        turno="TARDE",
        estado_ruta="PUBLICADA",
        numero=uniq_ruta_numero(),
        created_by_user_id=user_id,
    )
    db.session.add(ruta)
    db.session.flush()
    item = RutaItem(
        ruta_trabajo_id=ruta.id,
        iniciador_ruta_id=ini.id,
        orden_trabajo_id=ot.id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=user_id,
    )
    db.session.add(item)
    db.session.commit()
    ini_id = int(ini.id)

    _cerrar_local_cerrado(item.id, user_id)
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert iniciador_en_ruta_no_borrador_activa(ini_id) is None

    row = create_ruta_pool_dia_entry(
        fecha=fecha_ruta_aislada_mismo_anio(2095),
        turno_id=None,
        usuario_id=user_id,
        iniciador_ruta_id=ini_id,
    )
    assert row.estado == "EN_POOL"


def test_item_abierto_en_ruta_publicada_sigue_bloqueando(app_ctx) -> None:
    from tests.test_reinspeccion_oficio_reencolado import _mk_reinspeccion_oficio_en_ruta_publicada

    item, _act, ini, _u, _ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    ini_id = int(ini.id)
    item_id = int(item.id)
    db.session.expunge_all()

    bloqueante = iniciador_en_ruta_no_borrador_activa(ini_id)
    assert bloqueante is not None
    assert bloqueante.id == item_id

    ctx = build_estado_operativo_pool_por_iniciador([ini_id])[ini_id]
    assert ctx["estado_operativo_pool"] == "en_ruta_publicada"

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    ini_db.estado_iniciador = "PENDIENTE"
    db.session.commit()

    with pytest.raises(RuntimeError, match="ruta publicada"):
        validar_iniciador_elegible_para_pool(
            ini_db,
            fecha=fecha_ruta_aislada_mismo_anio(2094),
            turno_id=None,
        )


def test_realizado_cumplido_no_permite_pool(app_ctx) -> None:
    from tests.test_reinspeccion_oficio_reencolado import _mk_reinspeccion_oficio_en_ruta_publicada

    item, _act, ini, u, _ofi = _mk_reinspeccion_oficio_en_ruta_publicada()
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"tipo_actuacion": "VERIFICAR E INFORMAR"}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini.id)
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"

    ctx = build_estado_operativo_pool_por_iniciador([int(ini.id)])[int(ini.id)]
    assert ctx["estado_operativo_pool"] == "resuelto"

    with pytest.raises(RuntimeError, match="PENDIENTE"):
        validar_iniciador_elegible_para_pool(
            ini_db,
            fecha=fecha_ruta_aislada_mismo_anio(2093),
            turno_id=None,
        )


def test_pr11_ot_no_realizado_no_genera_conflicto_publicacion(app_ctx) -> None:
    """PR11 intacto: ítem FINALIZADO+NO_REALIZADO no bloquea OT en publicación."""
    from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
        buscar_conflicto_orden_trabajo_al_publicar,
    )
    from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
        _mk_iniciador_reinspeccion_notificacion,
        _publicar_y_cerrar_no_realizado,
        _setup_borrador_con_iniciador,
        _unique_num,
    )

    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    ini_id = int(ini.id)
    ruta1, item1 = _setup_borrador_con_iniciador(ini, numero_ot=_unique_num())
    act_prev = _publicar_y_cerrar_no_realizado(ruta1, item1, u.id)

    conflicto = buscar_conflicto_orden_trabajo_al_publicar(
        orden_trabajo_id=act_prev.orden_trabajo_id,
        ruta_item_id=999_999,
        iniciador_ruta_id=ini_id,
    )
    assert conflicto is None
