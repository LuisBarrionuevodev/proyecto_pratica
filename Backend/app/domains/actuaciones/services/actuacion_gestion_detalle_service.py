from __future__ import annotations

from app.domains.actuaciones.presenters.actuacion_gestion_seguimiento_presenter import (
    present_actuacion_gestion_detalle,
)
from app.domains.actuaciones.services.actuaciones_actuacion_inspector_scope import (
    assert_inspector_puede_acceder_actuacion,
)
from app.domains.actuaciones.utils.actuaciones_bandeja_eager import (
    reload_actuaciones_inspeccion_checklist_eager,
)
from app.models import Actuaciones


def obtener_actuacion_gestion_detalle(actuacion_id: int) -> dict:
    """
    Detalle autorizado de una actuación para el modal de Gestión (incluye seguimiento y teléfono).

    Parámetros:
        actuacion_id: PK de la actuación.

    Retorno:
        Fila de grilla enriquecida con ``ui_policy`` y ``seguimiento`` (teléfono solo en ``seguimiento``).

    Errores:
        ValueError: actuación no encontrada.
        InspectorScopeError: inspector sin acceso a la actuación.
    """
    assert_inspector_puede_acceder_actuacion(int(actuacion_id))
    act = Actuaciones.query.get(int(actuacion_id))
    if act is None:
        raise ValueError("Actuación no encontrada.")
    act_reload = reload_actuaciones_inspeccion_checklist_eager([act])[0]
    return present_actuacion_gestion_detalle(act_reload)
