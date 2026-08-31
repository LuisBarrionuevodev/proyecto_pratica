"""GESTIÓN-FIX.6.2 — PUT Oficio sin exigir domicilio; PUT residual tras corrección."""

from __future__ import annotations

import random
from uuid import uuid4

import pytest

from app.database import db
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.corregir_cierre_oficio_in import CorregirCierreOficioIn
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.corregir_cierre_oficio_service import corregir_cierre_oficio
from app.domains.actuaciones.services.oficio_circuito_service import (
    actuacion_es_circuito_reinspeccion_oficio,
)
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.models import Actuaciones, Inspector, Motivo

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_gestion_fix_3 import _ensure_catalog_contraproducencia


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _row_put_minimo_oficio(act: Actuaciones, *, tipo: str, insp_nombre: str) -> dict:
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else "000001"
    fecha = act.fecha.strftime("%d/%m/%Y") if act.fecha else "10/06/2026"
    return {
        "id": int(act.id),
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha,
        "tipo_actuacion": tipo,
        "inspector1": insp_nombre,
    }


def test_oficio_circuito_detectado_desde_actuacion(app_ctx) -> None:
    """Helper de circuito resuelve REINSPECCION_OFICIO desde RutaItem."""
    _item, act, _ini, _u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    assert actuacion_es_circuito_reinspeccion_oficio(int(act.id)) is True


def test_oficio_put_schema_sin_calle_con_contexto_ok(app_ctx) -> None:
    """PUT residual Verificar SI no exige calle/rubro/doc con contexto Oficio."""
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
        cerrar_completar_trabajo_por_ruta_item,
    )

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, int(act.id))
    assert act_db is not None

    insp = Inspector.query.first()
    assert insp is not None

    row_in = ActuacionGridRowIn.model_validate(
        _row_put_minimo_oficio(act_db, tipo="VERIFICAR E INFORMAR", insp_nombre=insp.nombre),
        context={"es_reinspeccion_oficio": True},
    )
    actualizar_actuacion(int(act.id), map_actuacion_row(row_in))
    db.session.expunge_all()

    act_after = db.session.get(Actuaciones, int(act.id))
    assert act_after is not None
    assert str(act_after.tipo) == "VERIFICAR E INFORMAR"


def test_oficio_put_calle_stale_sin_numero_con_contexto_ok(app_ctx) -> None:
    """Calle stale sin número no dispara validación de par en circuito Oficio."""
    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
        cerrar_completar_trabajo_por_ruta_item,
    )

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_db = db.session.get(Actuaciones, int(act.id))
    assert act_db is not None
    insp = Inspector.query.first()
    assert insp is not None

    payload = _row_put_minimo_oficio(act_db, tipo="VERIFICAR E INFORMAR", insp_nombre=insp.nombre)
    payload["calle"] = "San Martín"
    row_in = ActuacionGridRowIn.model_validate(
        payload,
        context={"es_reinspeccion_oficio": True},
    )
    assert row_in.calle == "San Martín"
    assert row_in.numero is None


def test_oficio_si_contra_put_residual_sin_domicilio(app_ctx) -> None:
    """Verificar SI→CONTRA tras corregir-cierre-oficio: PUT residual sin calle OK."""
    _ensure_catalog_contraproducencia("LOCAL CERRADO")
    motivo = Motivo.query.first()
    if motivo is None:
        pytest.skip("Se requiere motivo en catálogo")

    item, act, _ini, u = _mk_reinspeccion_oficio_item(uuid4().hex[:8])
    from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
        cerrar_completar_trabajo_por_ruta_item,
    )

    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "realizo_nueva_inspeccion": True,
                "acta_inspeccion_num": f"{random.randint(1000, 99999)}",
                "acta_notificacion_num": f"{random.randint(1000, 99999)}",
                "notificacion_motivo_1": motivo.nombre,
            }
        ),
        ejecutado_por_user_id=int(u.id),
    )
    db.session.expunge_all()
    act_id = int(act.id)

    corregir_cierre_oficio(
        act_id,
        CorregirCierreOficioIn.model_validate(
            {
                "tipo_actuacion": "VERIFICAR E INFORMAR",
                "contraproducencia": "LOCAL CERRADO",
                "realizo_nueva_inspeccion": None,
                "actas_a_quitar": ["INSPECCION", "NOTIFICACION"],
            }
        ),
    )
    db.session.expunge_all()

    act_db = db.session.get(Actuaciones, act_id)
    assert act_db is not None
    insp = Inspector.query.first()
    assert insp is not None

    row_in = ActuacionGridRowIn.model_validate(
        _row_put_minimo_oficio(act_db, tipo="VERIFICAR E INFORMAR", insp_nombre=insp.nombre),
        context={"es_reinspeccion_oficio": True},
    )
    actualizar_actuacion(act_id, map_actuacion_row(row_in))
    db.session.expunge_all()

    act_after = db.session.get(Actuaciones, act_id)
    assert act_after is not None
    assert (act_after.contraproducencia or "").strip().upper() == "LOCAL CERRADO"
