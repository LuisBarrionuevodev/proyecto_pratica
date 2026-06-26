"""Reinspección por oficio reencolada: bandeja y visibilidad tras contraproducencia."""

from __future__ import annotations

import random
from datetime import date

import pytest

from app.database import db
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.comprobacion_actas_bandeja_service import (
    list_pendientes_reinspeccion_oficio_filas,
)
from app.domains.actuaciones.services.oficio_editable_service import iniciador_en_ruta_operativa
from app.models import Actuaciones, IniciadorRuta, Oficio, RutaItem, RutaTrabajo, User


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def _mk_user() -> User:
    u = User(
        username=f"u_reenc_of_{_unique_num()}",
        email=f"reenc_of_{_unique_num()}@t.local",
        password_hash="x",
        role="usuario",
        is_active=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _mk_reinspeccion_oficio_en_ruta_publicada() -> tuple[RutaItem, Actuaciones, IniciadorRuta, User, Oficio]:
    """Circuito documental completo + iniciador en ruta PUBLICADA (listo para cerrar)."""
    from tests.test_comprobacion_pendientes_reinspeccion_bandeja import _mk_circuito_completo

    act_id, _nof, _jz_id = _mk_circuito_completo()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None and act.comprobacion_id is not None
    ofi = (
        Oficio.query.filter_by(comprobacion_id=act.comprobacion_id, deleted_at=None)
        .order_by(Oficio.id.desc())
        .first()
    )
    assert ofi is not None
    u = _mk_user()
    ini = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="EN_EJECUCION",
        fecha_origen=date(2026, 6, 10),
        anio=2026,
        mes=6,
        domicilio_id=act.domicilio_id,
        oficio_id=ofi.id,
        comprobacion_id=act.comprobacion_id,
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(ini)
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
        orden_trabajo_id=act.orden_trabajo_id,
        estado_ruta_item="EN_PROCESO",
        actuacion_id=act.id,
        created_by_user_id=u.id,
    )
    db.session.add(item)
    db.session.commit()
    return item, act, ini, u, ofi


def test_reencolado_contraproducencia_aparece_en_bandeja_reinspeccion(app_ctx) -> None:
    """
    Tras LOCAL CERRADO en REINSPECCION_OFICIO, el ítem FINALIZADO en ruta PUBLICADA no debe
    ocultar la fila de bandeja (iniciador PENDIENTE reencolado).
    """
    item, act, ini, u, ofi = _mk_reinspeccion_oficio_en_ruta_publicada()

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "contraproducencia": "LOCAL CERRADO",
            "tipo_actuacion": "VERIFICAR E INFORMAR",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )
    db.session.expunge_all()

    ini_db = db.session.get(IniciadorRuta, ini.id)
    item_db = db.session.get(RutaItem, item.id)
    assert ini_db is not None and ini_db.estado_iniciador == "PENDIENTE"
    assert item_db is not None and item_db.estado_ruta_item == "FINALIZADO"

    assert iniciador_en_ruta_operativa(ini_db) is False

    filas = list_pendientes_reinspeccion_oficio_filas(
        ActuacionesPendientesFilters(omitir_rango_fecha=True)
    )
    ids_oficio = {o.id for _act, o, _ini in filas if _act.id == act.id}
    assert ofi.id in ids_oficio


def test_iniciador_en_ruta_operativa_solo_cuenta_items_abiertos(app_ctx) -> None:
    """Ítem FINALIZADO en ruta PUBLICADA no implica «en ruta operativa»."""
    from uuid import uuid4

    from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item

    item, _act, ini, _u = _mk_reinspeccion_oficio_item(f"reenc_abierto_{uuid4().hex[:8]}")
    ruta = db.session.get(RutaTrabajo, item.ruta_trabajo_id)
    assert ruta is not None
    ruta.estado_ruta = "PUBLICADA"
    item.estado_ruta_item = "FINALIZADO"
    item.estado_ejecucion = "NO_REALIZADO"
    ini.estado_iniciador = "PENDIENTE"
    db.session.commit()

    assert iniciador_en_ruta_operativa(ini) is False

    item.estado_ruta_item = "EN_PROCESO"
    db.session.commit()
    assert iniciador_en_ruta_operativa(ini) is True
