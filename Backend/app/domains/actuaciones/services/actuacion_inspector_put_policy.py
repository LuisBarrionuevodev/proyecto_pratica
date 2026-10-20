from __future__ import annotations

from typing import Any

from flask import g

from app.domains.usuarios.security.decorators import resolve_user_from_identity
from app.domains.usuarios.security.inspector_scope_policy import InspectorScopeError
from app.domains.usuarios.services.inspector_link_service import INSPECTOR_ROLE

INSPECTOR_FORBIDDEN_PUT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "orden_trabajo",
        "orden_trabajo_numero",
        "orden_trabajo_id",
        "fecha_actuacion",
        "inspectores",
        "inspector1",
        "inspector2",
        "inspector3",
        "domicilio_id",
        "created_by_user_id",
        "created_at",
        "updated_at",
        "ruta_item_id",
        "iniciador_ruta_id",
        "ruta_trabajo_id",
        "actuacion_id",
    }
)

_INSPECTOR_FORBIDDEN_DETAIL = (
    "No tiene permisos para modificar campos de pertenencia u operación restringida."
)


def _inspector_forbidden_keys_in_mapping(data: dict[str, Any]) -> frozenset[str]:
    """Claves de primer nivel presentes en el body que el Inspector no puede enviar."""
    return INSPECTOR_FORBIDDEN_PUT_PAYLOAD_KEYS.intersection(data.keys())


def assert_inspector_raw_json_solo_campos_permitidos(raw: dict[str, Any]) -> None:
    """
    Rechaza claves estructurales en el JSON crudo del PUT antes de Pydantic (Inspector).

    Parámetros:
        raw: body JSON parseado (dict de primer nivel).

    Errores:
        InspectorScopeError: 403 si el inspector envía campos prohibidos.
    """
    user = resolve_user_from_identity()
    if user is None or user.role != INSPECTOR_ROLE:
        return
    forbidden = _inspector_forbidden_keys_in_mapping(raw)
    if forbidden:
        raise InspectorScopeError(_INSPECTOR_FORBIDDEN_DETAIL, status_code=403)


def hydrate_inspector_put_row_for_validation(actuacion_id: int, data: dict[str, Any]) -> None:
    """
    Completa en ``data`` campos de solo lectura exigidos por ``ActuacionGridRowIn`` que el Inspector
    no puede enviar en el JSON (p. ej. ``fecha_actuacion``).

    Parámetros:
        actuacion_id: PK de la actuación en edición.
        data: body del PUT (mutado in-place).

    Errores esperados: ninguno.
    """
    from app.models import Actuaciones

    act = Actuaciones.query.get(int(actuacion_id))
    if act is None:
        return
    if "fecha_actuacion" not in data and act.fecha is not None:
        data["fecha_actuacion"] = act.fecha.isoformat()
    ot = act.orden_trabajo
    if "orden_trabajo_numero" not in data and ot is not None:
        raw_ot = str(ot.numero_acta or "").strip()
        if raw_ot.isdigit():
            data["orden_trabajo_numero"] = raw_ot.zfill(6)
        else:
            digits = "".join(ch for ch in raw_ot if ch.isdigit())
            if digits:
                data["orden_trabajo_numero"] = digits[-6:].zfill(6)


def assert_inspector_payload_solo_campos_permitidos(payload: dict[str, Any]) -> None:
    """
    Rechaza claves estructurales en PUT de actuación cuando el actor es Inspector.

    Parámetros:
        payload: dict canon post-mapper (claves de negocio).

    Errores:
        InspectorScopeError: 403 si el inspector envía campos prohibidos.
    """
    user = resolve_user_from_identity()
    if user is None or user.role != INSPECTOR_ROLE:
        return
    client_keys = getattr(g, "inspector_put_client_keys", None)
    if client_keys is not None:
        forbidden = INSPECTOR_FORBIDDEN_PUT_PAYLOAD_KEYS.intersection(client_keys)
    else:
        forbidden = _inspector_forbidden_keys_in_mapping(payload)
    if forbidden:
        raise InspectorScopeError(_INSPECTOR_FORBIDDEN_DETAIL, status_code=403)
