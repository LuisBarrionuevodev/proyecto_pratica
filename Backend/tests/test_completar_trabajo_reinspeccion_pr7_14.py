"""PR7.14 — Cierre reinspección notificación/oficio sin cambio domicilio; parcial rechazado."""

from __future__ import annotations

import random
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
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Notificacion,
    OrdenTrabajo,
    RutaItem,
    RutaTrabajo,
    User,
)

from tests.test_completar_trabajo_stab4 import _mk_reinspeccion_oficio_item
from tests.test_hotfix_reinspeccion_notificacion import _mk_reinspeccion_notificacion_item


@pytest.fixture
def app_ctx():
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app
        db.session.rollback()


def _unique_num() -> str:
    return f"{random.randint(0, 999999):06d}"


def test_reinspeccion_notificacion_cierra_sin_cambio_domicilio(app_ctx) -> None:
    item, act, ini, u, noti = _mk_reinspeccion_notificacion_item()
    dom_id_antes = act.domicilio_id

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {"tipo_actuacion": "REINSPECCION", "acta_inspeccion_num": _unique_num()}
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    ini_db = IniciadorRuta.query.get(ini.id)
    item_db = RutaItem.query.get(item.id)

    assert act_db is not None
    assert act_db.domicilio_id == dom_id_antes
    assert act_db.notificacion_id == noti.id
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"
    assert item_db is not None and item_db.estado_ejecucion == "REALIZADO"


def test_reinspeccion_oficio_cierra_sin_cambio_domicilio(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, ini, u = _mk_reinspeccion_oficio_item(suf)
    dom_id_antes = act.domicilio_id

    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "acta_inspeccion_num": _unique_num(),
            "resultado_cumplimiento_oficio": "CUMPLE",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    ini_db = IniciadorRuta.query.get(ini.id)

    assert act_db is not None
    assert act_db.domicilio_id == dom_id_antes
    assert act_db.resultado_cumplimiento_oficio == "CUMPLE"
    assert ini_db is not None and ini_db.estado_iniciador == "CUMPLIDO"


def test_reinspeccion_notificacion_domicilio_parcial_falla(app_ctx) -> None:
    item, _act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "REINSPECCION",
            "acta_inspeccion_num": _unique_num(),
            "numero": "999",
        }
    )
    with pytest.raises(ValueError, match="calle y número completos|debe indicar la calle"):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )


def test_reinspeccion_oficio_domicilio_parcial_falla(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, _act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "acta_inspeccion_num": _unique_num(),
            "resultado_cumplimiento_oficio": "CUMPLE",
            "numero": "888",
        }
    )
    with pytest.raises(ValueError, match="calle y número completos|debe indicar la calle"):
        cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=item.id,
            payload=payload,
            ejecutado_por_user_id=u.id,
        )


def test_reinspeccion_notificacion_cambio_domicilio_completo(app_ctx) -> None:
    item, act, _ini, u, _noti = _mk_reinspeccion_notificacion_item()
    nueva_calle = f"Pr714Not{_unique_num()}"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "REINSPECCION",
            "acta_inspeccion_num": _unique_num(),
            "calle": nueva_calle,
            "numero": "42",
            "numero_tipo": "NUMERO",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    dom = Domicilio.query.get(act_db.domicilio_id) if act_db else None
    assert dom is not None
    assert dom.calle == nueva_calle
    assert dom.numero == "42"


def test_reinspeccion_oficio_cambio_domicilio_completo(app_ctx) -> None:
    suf = uuid4().hex[:8]
    item, act, _ini, u = _mk_reinspeccion_oficio_item(suf)
    nueva_calle = f"Pr714Ofi_{suf}"
    payload = CompletarTrabajoCierreCompletoIn.model_validate(
        {
            "tipo_actuacion": "VERIFICAR E INFORMAR",
            "acta_inspeccion_num": _unique_num(),
            "resultado_cumplimiento_oficio": "CUMPLE",
            "calle": nueva_calle,
            "numero": "77",
            "numero_tipo": "NUMERO",
        }
    )
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item.id,
        payload=payload,
        ejecutado_por_user_id=u.id,
    )

    db.session.expunge_all()
    act_db = Actuaciones.query.get(act.id)
    dom = Domicilio.query.get(act_db.domicilio_id) if act_db else None
    assert dom is not None
    assert dom.calle == nueva_calle
    assert dom.numero == "77"
