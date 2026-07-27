"""PR11.1b — Publicar ruta: NO_REALIZADO por contraproducencia no reserva OT (sin falso 409)."""

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
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.domains.rutas_trabajo.utils.ruta_publicar_debug import RutaPublicarDebugError
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Inspector,
    Notificacion,
    OrdenTrabajo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    User,
)

from tests.test_ruta_publicar_orden_trabajo_pr11_1 import (
    _dos_inspectores,
    _mk_iniciador_reinspeccion_notificacion,
    _mk_user,
    _publicar_y_cerrar_no_realizado,
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


def _migration_pr72_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("relevamiento")}
    return "nombre_fantasia" in cols and "angulo_esquina" in cols


@pytest.fixture
def require_pr72_migration(app_ctx):
    if not _migration_pr72_aplicada():
        pytest.skip("Requiere migración PR7.2 aplicada en BD")


def _inspector() -> Inspector:
    ins = Inspector.query.first()
    if ins is None:
        pytest.skip("Se requiere inspector en catálogo")
    return ins


def _cerrar_local_cerrado(item_id: int, user_id: int, *, tipo: str = "INSPECCION") -> None:
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": tipo}
            ),
            ejecutado_por_user_id=user_id,
        )


def _mk_iniciador_relevamiento() -> IniciadorRuta:
    rub = Rubro.query.first()
    if rub is None:
        pytest.skip("Se requiere rubro")
    ins = _inspector()
    rel = crear_relevamiento_desde_payload(
        {
            "fecha": "2026-07-10",
            "inspector_nombre": ins.nombre,
            "domicilio": {"calle": f"RelPr111b_{uuid4().hex[:8]}", "numero": "10"},
            "rubro_nombre": rub.nombre,
        }
    )
    ini = IniciadorRuta.query.filter_by(relevamiento_id=rel.id, deleted_at=None).first()
    assert ini is not None
    db.session.commit()
    return ini


def _mk_iniciador_denuncia() -> IniciadorRuta:
    u = _mk_user()
    with patch(
        "app.domains.denuncias.services.denuncias_service._get_current_user_id",
        return_value=u.id,
    ):
        _den, ini = crear_denuncia_con_iniciador(
            fecha=date(2026, 7, 10),
            domicilio_id=None,
            calle=f"DenPr111b_{uuid4().hex[:8]}",
            numero="20",
            interseccion=None,
            motivo="Prueba PR11.1b",
        )
    db.session.commit()
    return ini


def _publicar_cerrar_reencolar(
    ini: IniciadorRuta,
    *,
    ot_num: str,
    user_id: int,
    contra: str = "LOCAL CERRADO",
    tipo: str = "INSPECCION",
    fecha_ruta: date | None = None,
) -> Actuaciones:
    ruta, item = _setup_borrador_con_iniciador(ini, numero_ot=ot_num, fecha_ruta=fecha_ruta)
    publicar_ruta_trabajo(ruta_id=ruta.id)
    db.session.expire_all()
    item_db = RutaItem.query.get(item.id)
    assert item_db is not None and item_db.actuacion_id is not None
    act_id = int(item_db.actuacion_id)
    with patch(
        "app.domains.geolocalizacion.geocoding.services.geocode_orchestrator.on_domicilio_changed"
    ):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item_db.id,
            payload=CompletarTrabajoCierreCompletoIn.model_validate(
                {"contraproducencia": contra, "tipo_actuacion": tipo}
            ),
            ejecutado_por_user_id=user_id,
        )
    db.session.expire_all()
    act = Actuaciones.query.get(act_id)
    ini_db = IniciadorRuta.query.get(ini.id)
    item_db = RutaItem.query.get(item.id)
    assert act is not None
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert item_db is not None
    assert item_db.estado_ejecucion == "NO_REALIZADO"
    assert item_db.estado_ruta_item == "FINALIZADO"
    return act


@pytest.mark.parametrize(
    "mk_ini,tipo_cierre",
    [
        (_mk_iniciador_relevamiento, "INSPECCION"),
        (_mk_iniciador_denuncia, "INSPECCION"),
    ],
)
def test_pr11_1b_relevamiento_y_denuncia_republican_misma_ot(
    app_ctx, mk_ini, tipo_cierre
) -> None:
    ini = mk_ini()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ot_num = _unique_num()
    act_prev = _publicar_cerrar_reencolar(ini, ot_num=ot_num, user_id=u.id, tipo=tipo_cierre)

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    act_db = Actuaciones.query.get(act_prev.id)
    assert item2_db is not None and act_db is not None
    assert item2_db.actuacion_id == act_prev.id
    assert act_db.orden_trabajo_id == item2_db.orden_trabajo_id
    assert act_db.contraproducencia is None


def test_pr11_1b_reinspeccion_notificacion_local_cerrado_misma_ot(app_ctx) -> None:
    ini, _act_base, _noti, u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = _unique_num()
    act_prev = _publicar_y_cerrar_no_realizado(
        *_setup_borrador_con_iniciador(ini, numero_ot=ot_num)[:2],
        u.id,
        contra="LOCAL CERRADO",
    )
    _ = act_prev
    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta2.id)
    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None and item2_db.actuacion_id is not None


def test_pr11_1b_item_legacy_estado_ruta_no_realizado_republica(app_ctx) -> None:
    """Ítem legado con estado_ruta_item=NO_REALIZADO no debe provocar IntegrityError al republicar."""
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ot_num = _unique_num()
    act_prev = _publicar_cerrar_reencolar(ini, ot_num=ot_num, user_id=u.id)

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

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id == act_prev.id


def test_pr11_1b_ot_en_proceso_sigue_bloqueando(app_ctx) -> None:
    ini1 = _mk_iniciador_relevamiento()
    ot_num = _unique_num()
    ruta1, item1 = _setup_borrador_con_iniciador(ini1, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta1.id)
    db.session.expire_all()
    item1_db = RutaItem.query.get(item1.id)
    assert item1_db is not None

    ini2 = _mk_iniciador_relevamiento()
    ruta2, item2 = _setup_borrador_con_iniciador(ini2, numero_ot=_unique_num())
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    item2_db.orden_trabajo_id = item1_db.orden_trabajo_id
    db.session.commit()

    with pytest.raises(RuntimeError, match="actuación"):
        publicar_ruta_trabajo(ruta_id=ruta2.id)


def test_pr11_1b_item_soft_deleted_no_bloquea_ot(app_ctx) -> None:
    ini = _mk_iniciador_relevamiento()
    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ot_num = _unique_num()
    act_prev = _publicar_cerrar_reencolar(ini, ot_num=ot_num, user_id=u.id)

    item_prev = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.actuacion_id == act_prev.id,
        )
        .first()
    )
    assert item_prev is not None
    from datetime import datetime

    item_prev.deleted_at = datetime.utcnow()
    db.session.commit()

    ruta2, item2 = _setup_borrador_con_iniciador(ini, numero_ot=ot_num)
    publicar_ruta_trabajo(ruta_id=ruta2.id)

    db.session.expire_all()
    item2_db = RutaItem.query.get(item2.id)
    assert item2_db is not None
    assert item2_db.actuacion_id is not None


def test_pr11_1b_actuacion_base_sin_item_sigue_bloqueando_ot(app_ctx) -> None:
    """La inspección base de reinspección (sin ítem de ruta) sigue reservando su OT."""
    ini, act_base, _noti, _u = _mk_iniciador_reinspeccion_notificacion()
    ot_num = act_base.orden_trabajo.numero_acta
    assert ot_num is not None

    u = User.query.filter(User.is_active.is_(True)).first()
    assert u is not None
    ins1, ins2 = _dos_inspectores()
    ruta = RutaTrabajo(
        fecha=date(2026, 7, 21),
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
