"""GESTIÓN-FIX.10A.1 — múltiples intentos RN sobre la misma Notificación origen."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    sync_iniciadores_reinspeccion_notificacion,
)
from app.domains.rutas_trabajo.services.grupo_inspectores_service import replace_grupo_inspectores
from app.domains.rutas_trabajo.services.grupo_service import create_ruta_grupo
from app.domains.rutas_trabajo.services.ruta_item_orden_trabajo_service import (
    set_orden_trabajo_on_item,
)
from app.domains.rutas_trabajo.services.ruta_items_service import assign_iniciadores_to_grupo
from app.domains.rutas_trabajo.services.ruta_publicar_service import publicar_ruta_trabajo
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, OrdenTrabajo, RutaItem, RutaTrabajo

from tests.test_gestion_fix_5 import _republicar_iniciador_generico
from tests.test_gestion_fix_8 import _cerrar_rn_realizado
from tests.test_notificacion_oper_ruta_3 import _mk_iniciador_reinspeccion, _mk_notif_act, _mk_user
from tests.test_oper_ruta_6f_replanificacion import uniq_ruta_numero


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _dos_inspector_ids() -> list[int]:
    from app.models import Inspector

    rows = Inspector.query.limit(2).all()
    if len(rows) < 2:
        pytest.skip("Se requieren al menos 2 inspectores para publicar ruta")
    return [int(rows[0].id), int(rows[1].id)]


def _publicar_primer_intento_rn(
    *,
    fecha_ruta: date,
    user_id: int,
    ini_id: int,
) -> tuple[RutaItem, int]:
    """Publica ruta con un iniciador RN y devuelve (item, actuacion_id)."""
    ruta = RutaTrabajo(
        fecha=fecha_ruta,
        turno="MANIANA",
        estado_ruta="BORRADOR",
        numero=uniq_ruta_numero(),
        created_by_user_id=user_id,
    )
    db.session.add(ruta)
    db.session.flush()
    grupo = create_ruta_grupo(ruta_id=ruta.id, nombre=f"G_{uuid4().hex[:6]}", estado="ACTIVO")
    replace_grupo_inspectores(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        inspector_ids=_dos_inspector_ids(),
    )
    items = assign_iniciadores_to_grupo(
        ruta_id=ruta.id,
        grupo_id=grupo.id,
        iniciador_ids=[ini_id],
    )
    item = items[0]
    set_orden_trabajo_on_item(
        ruta_id=ruta.id,
        item_id=item.id,
        numero_orden_trabajo=_unique_num(),
    )
    db.session.commit()
    ruta_id = int(ruta.id)
    publicar_ruta_trabajo(ruta_id=ruta_id)
    db.session.expunge_all()
    item_db = (
        RutaItem.query.filter(RutaItem.ruta_trabajo_id == ruta_id)
        .order_by(RutaItem.id.desc())
        .first()
    )
    assert item_db is not None
    act_id = int(item_db.actuacion_id or 0)
    assert act_id
    return item_db, act_id


def _cerrar_local_cerrado(item_id: int, user_id: int) -> None:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=int(item_id),
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "REINSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()


def _mk_rn_chain() -> tuple[IniciadorRuta, Actuaciones, int, int]:
    """Crea notificación + iniciador RN; retorna (ini, act_base, user_id, notificacion_id)."""
    u = _mk_user()
    act_base, noti = _mk_notif_act(fecha=date(2026, 11, 1))
    ini = _mk_iniciador_reinspeccion(act_base, u)
    ini.notificacion_id = int(noti.id)
    db.session.commit()
    return ini, act_base, int(u.id), int(noti.id)


def test_rn1_publicar_segundo_intento_misma_notificacion_sin_integrity_error(app_ctx) -> None:
    """RN1: Act B distinta, misma notificacion_id, sin IntegrityError al republicar."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    ini, _act_base, user_id, noti_id = _mk_rn_chain()
    ini_id = int(ini.id)

    item_a, act_a_id = _publicar_primer_intento_rn(
        fecha_ruta=date(2026, 11, 5),
        user_id=user_id,
        ini_id=ini_id,
    )
    _cerrar_local_cerrado(int(item_a.id), user_id)

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    assert ini_db.estado_iniciador == "PENDIENTE"

    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2026, 11, 20))
    act_b_id = int(item_b.actuacion_id or 0)
    assert act_b_id
    assert act_b_id != act_a_id

    act_a = db.session.get(Actuaciones, act_a_id)
    act_b = db.session.get(Actuaciones, act_b_id)
    assert act_a is not None and act_b is not None
    assert int(act_a.notificacion_id or 0) == noti_id
    assert int(act_b.notificacion_id or 0) == noti_id
    assert str(act_a.tipo) == "REINSPECCION"
    assert str(act_b.tipo) == "REINSPECCION"


def test_rn2_historial_dos_actuaciones_misma_notificacion(app_ctx) -> None:
    """RN2: tras publicar B, A y B coexisten con misma notificacion_id."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    ini, _act_base, user_id, noti_id = _mk_rn_chain()
    ini_id = int(ini.id)

    item_a, act_a_id = _publicar_primer_intento_rn(
        fecha_ruta=date(2026, 12, 1),
        user_id=user_id,
        ini_id=ini_id,
    )
    _cerrar_local_cerrado(int(item_a.id), user_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2026, 12, 15))
    act_b_id = int(item_b.actuacion_id or 0)

    act_a = db.session.get(Actuaciones, act_a_id)
    act_b = db.session.get(Actuaciones, act_b_id)
    assert act_a is not None and act_b is not None
    assert act_a.contraproducencia == "LOCAL CERRADO"
    assert act_b.contraproducencia is None

    count = db.session.scalar(
        select(func.count())
        .select_from(Actuaciones)
        .where(
            Actuaciones.anio == 2026,
            Actuaciones.tipo == "REINSPECCION",
            Actuaciones.notificacion_id == noti_id,
        )
    )
    assert int(count or 0) >= 2


def test_rn3_segundo_intento_realizado_cumple_iniciador(app_ctx) -> None:
    """RN3: A LOCAL CERRADO, B REALIZADO → ini CUMPLIDO."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    ini, _act_base, user_id, _noti_id = _mk_rn_chain()
    ini_id = int(ini.id)

    item_a, act_a_id = _publicar_primer_intento_rn(
        fecha_ruta=date(2026, 10, 1),
        user_id=user_id,
        ini_id=ini_id,
    )
    _cerrar_local_cerrado(int(item_a.id), user_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2026, 10, 15))

    _cerrar_rn_realizado(
        item_id=int(item_b.id),
        user_id=user_id,
        acta_inspeccion=f"{random.randint(100000, 999999):06d}",
    )

    act_a = db.session.get(Actuaciones, act_a_id)
    act_b = db.session.get(Actuaciones, int(item_b.actuacion_id or 0))
    ini_final = db.session.get(IniciadorRuta, ini_id)
    assert act_a is not None and act_b is not None and ini_final is not None
    assert act_a.contraproducencia == "LOCAL CERRADO"
    assert act_b.contraproducencia is None
    assert ini_final.estado_iniciador == "CUMPLIDO"


def test_rn4_tercer_intento_tres_actuaciones_misma_notificacion(app_ctx) -> None:
    """RN4: A y B LOCAL CERRADO, C nuevo intento — tres actuaciones, misma notificacion_id."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    ini, _act_base, user_id, noti_id = _mk_rn_chain()
    ini_id = int(ini.id)

    item_a, act_a_id = _publicar_primer_intento_rn(
        fecha_ruta=date(2027, 1, 5),
        user_id=user_id,
        ini_id=ini_id,
    )
    _cerrar_local_cerrado(int(item_a.id), user_id)

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2027, 1, 10))
    _cerrar_local_cerrado(int(item_b.id), user_id)

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_c = _republicar_iniciador_generico(ini_db, user_id, date(2027, 1, 20))
    act_c_id = int(item_c.actuacion_id or 0)

    ids = {act_a_id, int(item_b.actuacion_id or 0), act_c_id}
    assert len(ids) == 3

    for act_id in ids:
        act = db.session.get(Actuaciones, act_id)
        assert act is not None
        assert int(act.notificacion_id or 0) == noti_id
        assert str(act.tipo) == "REINSPECCION"


def test_rn5_no_duplica_iniciador_rn_misma_notificacion(app_ctx) -> None:
    """RN5: sync no materializa un segundo iniciador bloqueante para la misma notificación."""
    ini, act_base, _user_id, noti_id = _mk_rn_chain()
    ini_id = int(ini.id)
    ini.notificacion_id = noti_id
    act_base.notificacion_id = noti_id
    db.session.commit()

    outcome = sync_iniciadores_reinspeccion_notificacion()
    assert outcome.created == 0

    count = db.session.scalar(
        select(func.count())
        .select_from(IniciadorRuta)
        .where(
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.notificacion_id == noti_id,
            IniciadorRuta.deleted_at.is_(None),
        )
    )
    assert int(count or 0) == 1

    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None


def test_rn6_ot_distinta_por_intento(app_ctx) -> None:
    """RN6: cada intento conserva OT propia (no reutiliza la del intento anterior)."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    ini, _act_base, user_id, _noti_id = _mk_rn_chain()
    ini_id = int(ini.id)

    item_a, act_a_id = _publicar_primer_intento_rn(
        fecha_ruta=date(2027, 2, 1),
        user_id=user_id,
        ini_id=ini_id,
    )
    _cerrar_local_cerrado(int(item_a.id), user_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert ini_db is not None
    item_b = _republicar_iniciador_generico(ini_db, user_id, date(2027, 2, 10))

    act_a = db.session.get(Actuaciones, act_a_id)
    act_b = db.session.get(Actuaciones, int(item_b.actuacion_id or 0))
    assert act_a is not None and act_b is not None
    assert act_a.orden_trabajo_id is not None
    assert act_b.orden_trabajo_id is not None
    assert int(act_a.orden_trabajo_id) != int(act_b.orden_trabajo_id)

    ot_a = db.session.get(OrdenTrabajo, int(act_a.orden_trabajo_id))
    ot_b = db.session.get(OrdenTrabajo, int(act_b.orden_trabajo_id))
    assert ot_a is not None and ot_b is not None
    assert ot_a.numero_acta != ot_b.numero_acta
