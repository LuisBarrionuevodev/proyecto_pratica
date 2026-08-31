"""Corrección de cierre operativo desde PUT Actuaciones (limpiar contraproducencia)."""

from __future__ import annotations

import random
from datetime import date
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_corregir_cierre_operativo_service import (
    CorregirCierreOperativoError,
    MSG_REINGRESO_EN_RUTA,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.rutas_trabajo.services.iniciadores_pendientes_service import (
    planificable_iniciadores_base_query,
)
from app.models import Actuaciones, IniciadorRuta, Inspector, RutaItem, RutaTrabajo

from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada


def _fila_correccion(*, act_id: int, ot: str, fecha: str, insp1: str, insp2: str) -> dict:
    return {
        "id": act_id,
        "orden_trabajo_numero": ot,
        "fecha_actuacion": fecha,
        "tipo_actuacion": "INSPECCION",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "contrib_apellido": "Titular",
        "contrib_nombre": "Prueba",
        "inspector1": insp1,
        "inspector2": insp2,
        "acta_inspeccion_num": f"{random.randint(0, 999999):06d}",
        "limpiar_contraproducencia": True,
        "contraproducencia": None,
    }


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def test_mapper_incluye_limpiar_contraproducencia(app_ctx) -> None:
    ins = Inspector.query.limit(2).all()
    if len(ins) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    data = _fila_correccion(
        act_id=1, ot="123456", fecha="31/12/2025", insp1=ins[0].nombre, insp2=ins[1].nombre
    )
    row = ActuacionGridRowIn.model_validate(data)
    payload = map_actuacion_row(row)
    assert payload.get("limpiar_contraproducencia") is True
    assert "contraproducencia" in payload
    assert payload["contraproducencia"] is None


def test_limpiar_contraproducencia_reencolada_resuelve_iniciador(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()

    ini_pre = db.session.get(IniciadorRuta, ini_id)
    assert ini_pre is not None and ini_pre.estado_iniciador == "PENDIENTE"
    planif_antes = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id in planif_antes

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    row = ActuacionGridRowIn.model_validate(
        _fila_correccion(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=inspectores[0].nombre,
            insp2=inspectores[1].nombre,
        )
    )
    payload = map_actuacion_row(row)
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert act_db is not None
    assert act_db.contraproducencia is None
    assert act_db.inspeccion is not None
    assert item_db is not None
    assert item_db.estado_ejecucion == "REALIZADO"
    assert item_db.motivo_no_realizado is None
    assert ini_db is not None
    assert ini_db.estado_iniciador == "CUMPLIDO"
    planif_despues = {row.id for row in planificable_iniciadores_base_query().all()}
    assert ini_id not in planif_despues


def test_limpiar_contraproducencia_cancela_reintento_planificado_en_ruta_publicada(app_ctx) -> None:
    """FIX.9: ítem posterior planificado en ruta publicada se cancela al corregir Act A."""
    suf = uuid4().hex[:8]
    item_id, act_id, ini_id, user_id, _ruta_borrador_id, _dom_id = _mk_relevamiento_en_ruta_publicada(suf)
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {"contraproducencia": "LOCAL CERRADO", "tipo_actuacion": "INSPECCION"}
        ),
        ejecutado_por_user_id=user_id,
    )

    ruta_pub = RutaTrabajo(
        fecha=date(2026, 6, 20),
        turno="MANIANA",
        estado_ruta="PUBLICADA",
        created_by_user_id=user_id,
        numero=random.randint(2, 32000),
    )
    db.session.add(ruta_pub)
    db.session.flush()
    item_abierto = RutaItem(
        ruta_trabajo_id=ruta_pub.id,
        iniciador_ruta_id=ini_id,
        estado_ruta_item="PENDIENTE_ASIGNACION",
        created_by_user_id=user_id,
    )
    db.session.add(item_abierto)
    db.session.commit()
    item_abierto_id = int(item_abierto.id)

    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    row = ActuacionGridRowIn.model_validate(
        _fila_correccion(
            act_id=act_id,
            ot=ot_num,
            fecha=fecha,
            insp1=inspectores[0].nombre,
            insp2=inspectores[1].nombre,
        )
    )
    payload = map_actuacion_row(row)
    actualizar_actuacion(act_id, payload)
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    item_abierto_db = db.session.get(RutaItem, item_abierto_id)
    assert act_db is not None
    assert act_db.contraproducencia is None
    assert ini_db is not None
    assert ini_db.estado_iniciador == "CUMPLIDO"
    assert item_abierto_db is not None
    assert item_abierto_db.deleted_at is not None
