"""Reglas de prioridad / elegible_urgente para Planificación."""

from app.domains.rutas_trabajo.utils.planificacion_prioridad import (
    elegible_urgente_planificacion,
    prioridad_categoria_from_value,
)


def test_prioridad_categoria_escala():
    assert prioridad_categoria_from_value(1) == "BAJA"
    assert prioridad_categoria_from_value(2) == "MEDIA"
    assert prioridad_categoria_from_value(3) == "ALTA"
    assert prioridad_categoria_from_value(99) == "ALTA"


def test_elegible_urgente_relevamiento_nunca():
    assert elegible_urgente_planificacion("RELEVAMIENTO", 3) is False
    assert elegible_urgente_planificacion("RELEVAMIENTO", 1) is False


def test_elegible_urgente_denuncia_alta():
    assert elegible_urgente_planificacion("DENUNCIA", 3) is True
    assert elegible_urgente_planificacion("DENUNCIA", 2) is False
