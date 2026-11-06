"""V1.1-INSPECCION.1 — carácter de quien atendió y contrato de residuos."""

from __future__ import annotations

import random
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.database import db
from app.domains.actuaciones.mappers.completar_trabajo_cierre_mapper import (
    map_completar_trabajo_cierre_to_aplicar_payload,
)
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.utils.inspeccion_atencion import (
    MSG_ATENCION_REQUIERE_ACTA_INSPECCION,
    MSG_CARACTER_PERSONA_ATENDIO_INVALIDO,
)
from app.models import Actuaciones, CatalogTipoActuacion, Inspeccion, RutaItem
from tests.test_hotfix_reencolado_planificacion import _mk_relevamiento_en_ruta_publicada
from tests.test_inspeccion_checklist import (
    _base_create_payload,
    _put_actuacion,
)


@pytest.fixture(autouse=True)
def _seed_tipo_inspeccion(app_ctx):
    if CatalogTipoActuacion.query.filter_by(nombre="INSPECCION").first() is None:
        db.session.add(CatalogTipoActuacion(nombre="INSPECCION"))
        db.session.commit()


def _ins(act) -> Inspeccion:
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None
    return ins


def test_create_encargado_contrato_si(app_ctx):
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            caracter_persona_atendio="ENCARGADO",
            posee_contrato_retiro_residuos_solidos_urbanos=True,
        )
    )
    ins = _ins(act)
    assert ins.caracter_persona_atendio == "ENCARGADO"
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is True
    row = actuacion_to_grid_row(act)
    assert row["caracter_persona_atendio"] == "ENCARGADO"
    assert row["posee_contrato_retiro_residuos_solidos_urbanos"] is True


def test_create_otro_contrato_no(app_ctx):
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            caracter_persona_atendio="OTRO",
            posee_contrato_retiro_residuos_solidos_urbanos=False,
        )
    )
    ins = _ins(act)
    assert ins.caracter_persona_atendio == "OTRO"
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is False
    row = actuacion_to_grid_row(act)
    assert row["caracter_persona_atendio"] == "OTRO"
    assert row["posee_contrato_retiro_residuos_solidos_urbanos"] is False


def test_create_sin_indicar_queda_null(app_ctx):
    act = crear_actuacion_desde_payload(_base_create_payload())
    ins = _ins(act)
    assert ins.caracter_persona_atendio is None
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is None
    row = actuacion_to_grid_row(act)
    assert row["caracter_persona_atendio"] is None
    assert row["posee_contrato_retiro_residuos_solidos_urbanos"] is None


def test_edit_solo_atencion_en_inspeccion_existente(app_ctx):
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            caracter_persona_atendio="TITULAR",
            posee_contrato_retiro_residuos_solidos_urbanos=True,
        )
    )
    _put_actuacion(
        act,
        caracter_persona_atendio="EMPLEADO",
        posee_contrato_retiro_residuos_solidos_urbanos=False,
    )
    ins = _ins(act)
    assert ins.caracter_persona_atendio == "EMPLEADO"
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is False


def test_edit_otros_datos_sin_enviar_atencion_preserva_valores(app_ctx):
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            caracter_persona_atendio="ENCARGADO",
            posee_contrato_retiro_residuos_solidos_urbanos=True,
        )
    )
    _put_actuacion(act, nombre_local="Local Test")
    ins = _ins(act)
    assert ins.caracter_persona_atendio == "ENCARGADO"
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is True


def test_limpiar_con_null_persiste_sin_indicar(app_ctx):
    act = crear_actuacion_desde_payload(
        _base_create_payload(
            caracter_persona_atendio="TITULAR",
            posee_contrato_retiro_residuos_solidos_urbanos=True,
        )
    )
    _put_actuacion(
        act,
        caracter_persona_atendio=None,
        posee_contrato_retiro_residuos_solidos_urbanos=None,
    )
    ins = _ins(act)
    assert ins.caracter_persona_atendio is None
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is None


def test_create_schema_rechaza_caracter_invalido(app_ctx):
    with pytest.raises(ValidationError) as exc:
        ActuacionGridRowIn.model_validate(
            {
                "orden_trabajo_numero": f"{random.randint(0, 999999):06d}",
                "fecha_actuacion": "2026-09-09",
                "tipo_actuacion": "INSPECCION",
                "caracter_persona_atendio": "GERENTE",
            }
        )
    assert MSG_CARACTER_PERSONA_ATENDIO_INVALIDO in str(exc.value)


def test_rechaza_atencion_sin_acta_inspeccion(app_ctx):
    payload = _base_create_payload(
        caracter_persona_atendio="TITULAR",
        posee_contrato_retiro_residuos_solidos_urbanos=True,
    )
    payload.pop("acta_inspeccion_num", None)
    with pytest.raises(ValidationError) as exc:
        crear_actuacion_desde_payload(payload)
    assert MSG_ATENCION_REQUIERE_ACTA_INSPECCION in str(exc.value)


def test_put_atencion_sin_acta_inspeccion_422(app_ctx):
    payload = _base_create_payload()
    payload.pop("acta_inspeccion_num", None)
    act = crear_actuacion_desde_payload(payload)
    assert Inspeccion.query.filter_by(actuacion_id=act.id).first() is None
    with pytest.raises(ValidationError) as exc:
        _put_actuacion(act, caracter_persona_atendio="ENCARGADO")
    assert MSG_ATENCION_REQUIERE_ACTA_INSPECCION in str(exc.value)


def test_completar_trabajo_persiste_y_se_lee(app_ctx):
    suf = uuid4().hex[:8]
    item_id, act_id, _ini_id, user_id, _rb, _dom = _mk_relevamiento_en_ruta_publicada(suf)
    acta = f"{random.randint(100000, 999999):06d}"
    cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=item_id,
        payload=CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": acta,
                "caracter_persona_atendio": "ENCARGADO",
                "posee_contrato_retiro_residuos_solidos_urbanos": True,
                "solicita_carnet_manipulador": False,
                "doc_nro": "20123456789",
                "contrib_apellido": "Apellido",
                "contrib_nombre": "Nombre",
            }
        ),
        ejecutado_por_user_id=user_id,
    )
    db.session.expunge_all()
    act = db.session.get(Actuaciones, act_id)
    assert act is not None
    ins = Inspeccion.query.filter_by(actuacion_id=act.id).first()
    assert ins is not None
    assert ins.caracter_persona_atendio == "ENCARGADO"
    assert ins.posee_contrato_retiro_residuos_solidos_urbanos is True
    row = actuacion_to_grid_row(act)
    assert row["caracter_persona_atendio"] == "ENCARGADO"
    assert row["posee_contrato_retiro_residuos_solidos_urbanos"] is True
    item = db.session.get(RutaItem, item_id)
    assert item is not None


def test_cierre_schema_rechaza_caracter_invalido(app_ctx):
    with pytest.raises(ValidationError) as exc:
        CompletarTrabajoCierreCompletoIn.model_validate(
            {
                "tipo_actuacion": "INSPECCION",
                "acta_inspeccion_num": "123456",
                "caracter_persona_atendio": "JEFE",
            }
        )
    assert MSG_CARACTER_PERSONA_ATENDIO_INVALIDO in str(exc.value)


def test_cierre_mapper_incluye_atencion_solo_si_viene():
    act = MagicMock()
    act.domicilio = None
    ini = MagicMock()
    ini.domicilio = None
    row = CompletarTrabajoCierreCompletoIn.model_construct(
        tipo_actuacion="INSPECCION",
        acta_inspeccion_num="000042",
        caracter_persona_atendio="TITULAR",
        posee_contrato_retiro_residuos_solidos_urbanos=False,
    )
    payload = map_completar_trabajo_cierre_to_aplicar_payload(row, act=act, ini=ini)
    assert payload["caracter_persona_atendio"] == "TITULAR"
    assert payload["posee_contrato_retiro_residuos_solidos_urbanos"] is False

    row_sin = CompletarTrabajoCierreCompletoIn.model_construct(
        tipo_actuacion="INSPECCION",
        acta_inspeccion_num="000043",
    )
    payload_sin = map_completar_trabajo_cierre_to_aplicar_payload(row_sin, act=act, ini=ini)
    assert "caracter_persona_atendio" not in payload_sin
    assert "posee_contrato_retiro_residuos_solidos_urbanos" not in payload_sin


def test_put_mapper_omite_atencion_si_no_viene():
    row = ActuacionGridRowIn.model_construct(
        id=1,
        orden_trabajo_numero="000001",
        fecha_actuacion=date(2026, 9, 9),
        tipo_actuacion="INSPECCION",
        inspectores=["X"],
    )
    payload = map_actuacion_row(row)
    assert "caracter_persona_atendio" not in payload
    assert "posee_contrato_retiro_residuos_solidos_urbanos" not in payload
