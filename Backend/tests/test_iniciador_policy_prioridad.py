"""Policy de prioridad numérica alineada a Planificación (1=BAJA, 3+=ALTA)."""

import pytest

from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    VALOR_PRIORIDAD_ALTA,
    VALOR_PRIORIDAD_BAJA,
    priority_for_tipo,
)
from app.domains.rutas_trabajo.utils.planificacion_prioridad import prioridad_categoria_from_value


def test_relevamiento_es_baja_en_escala_planificacion():
    assert priority_for_tipo("RELEVAMIENTO") == VALOR_PRIORIDAD_BAJA
    assert prioridad_categoria_from_value(priority_for_tipo("RELEVAMIENTO")) == "BAJA"


def test_denuncia_y_reinspeccion_son_alta():
    assert priority_for_tipo("DENUNCIA") == VALOR_PRIORIDAD_ALTA
    assert priority_for_tipo("REINSPECCION_NOTIFICACION") == VALOR_PRIORIDAD_ALTA
    assert prioridad_categoria_from_value(priority_for_tipo("DENUNCIA")) == "ALTA"


def test_derivados_oficio_alta():
    for tipo in (
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        assert priority_for_tipo(tipo) == VALOR_PRIORIDAD_ALTA
        assert prioridad_categoria_from_value(priority_for_tipo(tipo)) == "ALTA"


def test_tipo_desconocido_falla():
    with pytest.raises(ValueError):
        priority_for_tipo("TIPO_INVENTADO")
