"""Filtros M3 urgentes — schema y reglas de tipo."""

from app.domains.rutas_trabajo.schemas.planificacion_in import PlanificacionUrgentesQuery


def test_planificacion_urgentes_query_filtros_opcionales():
    q = PlanificacionUrgentesQuery.model_validate(
        {
            "tipo_urgente": "denuncia",
            "q": "  san martin ",
            "numero_oficio": " 123 ",
            "numero_comprobacion": "004521",
        }
    )
    assert q.tipo_urgente == "DENUNCIA"
    assert q.q == "san martin"
    assert q.numero_oficio == "123"
    assert q.numero_comprobacion == "004521"


def test_planificacion_urgentes_query_vacio_no_rompe():
    q = PlanificacionUrgentesQuery.model_validate({})
    assert q.tipo_urgente is None
    assert q.q is None
    assert q.numero_oficio is None
    assert q.numero_comprobacion is None
    assert q.page == 1
    assert q.per_page == 25


def test_tipo_urgente_oficio_valido():
    q = PlanificacionUrgentesQuery.model_validate({"tipo_urgente": "OFICIO"})
    assert q.tipo_urgente == "OFICIO"


def test_tipo_urgente_notificacion_valido():
    q = PlanificacionUrgentesQuery.model_validate({"tipo_urgente": "notificacion"})
    assert q.tipo_urgente == "NOTIFICACION"
