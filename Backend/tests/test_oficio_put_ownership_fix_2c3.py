"""GESTIÓN-FIX.2C.3 — ownership PUT Oficio + reparación CUMPLE/contra."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.services.actas_canal_payload_guard import MSG_OFICIO_OPERATIVO_PUT
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import Actuaciones, CatalogContraproducencia, IniciadorRuta, Inspector, RutaItem

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _ensure_catalog_contraproducencia(nombre: str) -> None:
    if not CatalogContraproducencia.query.filter_by(nombre=nombre).first():
        db.session.add(CatalogContraproducencia(nombre=nombre))
        db.session.commit()


def _cerrar_item(item: RutaItem, user_id: int, payload: dict) -> Actuaciones:
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(payload),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    item_db = db.session.get(RutaItem, item.id)
    assert item_db is not None and item_db.actuacion_id is not None
    act = db.session.get(Actuaciones, item_db.actuacion_id)
    assert act is not None
    return act


def _corregir(act: Actuaciones, body: dict) -> Actuaciones:
    act_id = int(act.id)
    payload = CorregirCierreOficioIn.model_validate(body)
    corregir_cierre_oficio(act_id, payload)
    db.session.expunge_all()
    refreshed = db.session.get(Actuaciones, act_id)
    assert refreshed is not None
    return refreshed


def _put_minimo_oficio(act: Actuaciones) -> dict:
    inspectores = Inspector.query.limit(2).all()
    if len(inspectores) < 2:
        pytest.skip("Se requieren al menos 2 inspectores en catálogo")
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    return {
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha,
        "tipo_actuacion": act.tipo,
        "rubro_nombre": "Bar",
        "inspectores": [inspectores[0].nombre, inspectores[1].nombre],
        "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
    }


def test_put_oficio_rechaza_contraproducencia(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()
    act_id = int(act_cerrada.id)

    with pytest.raises(ValueError, match="corrección de cierre"):
        actualizar_actuacion(act_id, {"contraproducencia": "LOCAL CERRADO"})

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.contraproducencia == "LOCAL CERRADO"


def test_put_oficio_rechaza_limpiar_contraproducencia(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()

    with pytest.raises(ValueError, match=MSG_OFICIO_OPERATIVO_PUT):
        actualizar_actuacion(
            int(act_cerrada.id),
            {"limpiar_contraproducencia": True, "contraproducencia": None},
        )


def test_e2e_corregir_cumple_put_sin_contra_persiste(app_ctx) -> None:
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "contraproducencia": "LOCAL CERRADO",
        },
    )
    ini.tipo_iniciador = "RATIFICACION_CLAUSURA_OFICIO"
    db.session.commit()
    act_id = int(act_cerrada.id)

    act_corr = _corregir(
        act_cerrada,
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    assert act_corr.contraproducencia is None
    assert act_corr.resultado_cumplimiento_oficio == "CUMPLE"

    actualizar_actuacion(act_id, _put_minimo_oficio(act_corr))
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    assert act_db.resultado_cumplimiento_oficio == "CUMPLE"
    assert act_db.contraproducencia is None

    row = actuacion_to_grid_row(act_db)
    assert row.get("contraproducencia") in (None, "")
    assert row.get("resultado_cumplimiento_oficio") == "CUMPLE"


def test_repair_cumple_contraproducencia_sql(app_ctx) -> None:
    """Lógica de migración e5f6a7b8c9d0: CUMPLE + contra → contra NULL."""
    item, act, ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    act_cerrada = _cerrar_item(
        item,
        int(u.id),
        {
            "tipo_actuacion": "RATIFICACION DE CLAUSURA",
            "resultado_cumplimiento_oficio": "CUMPLE",
        },
    )
    act_id = int(act_cerrada.id)
    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    act_db.contraproducencia = "LOCAL CERRADO"
    db.session.commit()

    item_id = item.id
    ini_id = ini.id
    tipo_ini = ini.tipo_iniciador
    estado_ini = db.session.get(IniciadorRuta, ini_id).estado_iniciador

    count = db.session.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM actuaciones
            WHERE id = :aid
              AND resultado_cumplimiento_oficio = 'CUMPLE'
              AND contraproducencia IS NOT NULL
              AND TRIM(contraproducencia) != ''
            """
        ),
        {"aid": act_id},
    ).scalar()
    assert int(count or 0) == 1

    db.session.execute(
        sa.text(
            """
            UPDATE actuaciones
            SET contraproducencia = NULL
            WHERE resultado_cumplimiento_oficio = 'CUMPLE'
              AND contraproducencia IS NOT NULL
              AND TRIM(contraproducencia) != ''
              AND id = :aid
            """
        ),
        {"aid": act_id},
    )
    db.session.commit()
    db.session.expunge_all()

    act_repaired = db.session.get(Actuaciones, act_id)
    assert act_repaired is not None
    assert act_repaired.contraproducencia is None
    assert act_repaired.resultado_cumplimiento_oficio == "CUMPLE"
    assert str(act_repaired.tipo) == "RATIFICACION DE CLAUSURA"

    item_db = db.session.get(RutaItem, item_id)
    ini_db = db.session.get(IniciadorRuta, ini_id)
    assert item_db is not None
    assert ini_db is not None
    assert ini_db.tipo_iniciador == tipo_ini
    assert ini_db.estado_iniciador == estado_ini
