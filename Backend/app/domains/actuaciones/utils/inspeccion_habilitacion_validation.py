"""Validación obligatoria de TIENE_HABILITACION en actas de inspección reales."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.models import Actuaciones, Inspeccion, ItemActaInspeccion

MSG_TIENE_HABILITACION = "Indicá si el establecimiento tiene habilitación."
_CODIGO_TIENE_HABILITACION = "TIENE_HABILITACION"


def _validation_error_items_acta_inspeccion() -> ValidationError:
    return ValidationError.from_exception_data(
        "InspeccionChecklist",
        [
            {
                "type": "value_error",
                "loc": ("items_acta_inspeccion",),
                "msg": "Value error",
                "input": None,
                "ctx": {"error": MSG_TIENE_HABILITACION},
            }
        ],
    )


def _item_id_tiene_habilitacion() -> int | None:
    row = ItemActaInspeccion.query.filter_by(codigo=_CODIGO_TIENE_HABILITACION).first()
    return int(row.id) if row is not None else None


def _tiene_respuesta_habilitacion(requested: list[dict[str, Any]], id_hab: int) -> bool:
    for req in requested:
        if int(req["item_id"]) != id_hab:
            continue
        valor = req.get("valor_si_no")
        return isinstance(valor, bool)
    return False


def exigir_tiene_habilitacion_inspeccion_real(actuacion: Actuaciones, payload: dict[str, Any]) -> bool:
    """
    True si el payload intenta registrar/modificar checklist de una inspección real (sin contraproducencia).
    """
    if (actuacion.contraproducencia or "").strip():
        return False
    inspeccion = Inspeccion.query.filter_by(actuacion_id=int(actuacion.id)).first()
    if inspeccion is None and not (payload.get("acta_inspeccion_num") or "").strip():
        return False
    if "items_acta_inspeccion" in payload:
        return True
    if (payload.get("acta_inspeccion_num") or "").strip():
        return True
    return False


def validar_tiene_habilitacion_obligatoria(
    actuacion: Actuaciones,
    payload: dict[str, Any],
    requested: list[dict[str, Any]],
) -> None:
    """
    Exige respuesta SI/NO al ítem TIENE_HABILITACION cuando aplica inspección real.

    Errores:
        ValidationError: 422 con loc items_acta_inspeccion.
    """
    if not exigir_tiene_habilitacion_inspeccion_real(actuacion, payload):
        return
    id_hab = _item_id_tiene_habilitacion()
    if id_hab is None:
        return
    if _tiene_respuesta_habilitacion(requested, id_hab):
        return
    raise _validation_error_items_acta_inspeccion()
