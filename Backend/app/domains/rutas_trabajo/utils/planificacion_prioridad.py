"""
Reglas de prioridad y bandeja de urgentes para Planificación (Rutas de trabajo).

Escala persistida en `IniciadorRuta.prioridad`: 1=BAJA, 2=MEDIA, 3+=ALTA.
Los valores al crearse deben seguir `iniciador_policy_service.priority_for_tipo` (misma escala).
"""

from __future__ import annotations


def prioridad_categoria_from_value(prioridad: int | None) -> str:
    """
    Deriva etiqueta BAJA | MEDIA | ALTA desde el valor numérico en DB.

    Parámetros:
        prioridad: valor SmallInteger; None se trata como BAJA.

    Retorno:
        'BAJA' | 'MEDIA' | 'ALTA'
    """
    if prioridad is None:
        return "BAJA"
    if prioridad <= 1:
        return "BAJA"
    if prioridad == 2:
        return "MEDIA"
    return "ALTA"


def elegible_urgente_planificacion(tipo_iniciador: str | None, prioridad: int | None) -> bool:
    """
    Panel derecho de urgentes: relevamiento nunca entra; resto requiere prioridad ALTA (>= 3).

    Parámetros:
        tipo_iniciador: enum IniciadorRuta.tipo_iniciador.
        prioridad: valor en DB.

    Retorno:
        True si puede mostrarse en bandeja urgentes (API planificacion/urgentes).
    """
    if not tipo_iniciador or tipo_iniciador == "RELEVAMIENTO":
        return False
    p = prioridad if prioridad is not None else 1
    return p >= 3
