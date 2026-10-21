"""Mapper Inspector PATCH → payload canónico de update (sin OT/fecha/inspectores)."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.schemas.actuacion_inspector_patch_in import ActuacionInspectorPatchIn
from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.services.actuacion_inspector_put_policy import (
    INSPECTOR_FORBIDDEN_PUT_PAYLOAD_KEYS,
)

_PLACEHOLDER_FECHA = date(1970, 1, 1)


def map_inspector_patch_to_canonical(patch: ActuacionInspectorPatchIn) -> Dict[str, Any]:
    """
    Convierte el patch validado del Inspector al dict que consume ``aplicar_payload_actuacion``.

    Parámetros:
        patch: entrada validada con solo campos editables.

    Retorno:
        Payload parcial sin claves prohibidas para Inspector (inspectores, fecha, OT, id).

    Errores esperados: ninguno (validación ya ocurrió en Pydantic).
    """
    patch_data = patch.model_dump(exclude_unset=True)
    row = ActuacionGridRowIn.model_construct(
        fecha_actuacion=_PLACEHOLDER_FECHA,
        **patch_data,
    )
    payload = map_actuacion_row(row)
    for key in INSPECTOR_FORBIDDEN_PUT_PAYLOAD_KEYS:
        payload.pop(key, None)
    payload.pop("carga_solo_comprobacion", None)
    return payload
