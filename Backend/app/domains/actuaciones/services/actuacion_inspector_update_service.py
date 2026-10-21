"""Actualización de actuación para Inspector (campos parciales; inspectores inmutables)."""

from __future__ import annotations

from typing import Any

from app.domains.actuaciones.services.update_service import actualizar_actuacion


def actualizar_actuacion_inspector(
    actuacion_id: int,
    payload: dict[str, Any],
    *,
    actor_user_id: int | None = None,
):
    """
    Aplica un PUT parcial del Inspector sin tocar inspectores ni metadatos de pertenencia.

    Parámetros:
        actuacion_id: PK de la actuación.
        payload: dict canónico post-mapper (solo campos enviados por el cliente).
        actor_user_id: usuario autenticado (auditoría).

    Retorno:
        Entidad ``Actuaciones`` persistida.

    Errores esperados: mismos que ``actualizar_actuacion`` (ValueError, InspectorScopeError, etc.).
    """
    safe = dict(payload)
    safe.pop("inspectores", None)
    safe.pop("fecha_actuacion", None)
    safe.pop("orden_trabajo_numero", None)
    safe.pop("id", None)
    return actualizar_actuacion(actuacion_id, safe, actor_user_id=actor_user_id)
