"""Validación obligatoria de TIENE_HABILITACION en actas de inspección reales."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.domains.actuaciones.utils.circuito_operativo import (
    CIRCUITO_REINSPECCION_NOTIFICACION,
    CIRCUITO_REINSPECCION_OFICIO,
    circuito_desde_actuacion_id,
)
from app.models import ActaInspeccionItem, Actuaciones, Inspeccion, ItemActaInspeccion

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


def _circuito_exime_habilitacion(actuacion: Actuaciones) -> bool:
    if not actuacion.id:
        return False
    circuito = circuito_desde_actuacion_id(int(actuacion.id))
    return circuito in (CIRCUITO_REINSPECCION_NOTIFICACION, CIRCUITO_REINSPECCION_OFICIO)


def _persisted_valor_si_no_habilitacion(actuacion: Actuaciones, id_hab: int) -> bool | None:
    inspeccion = Inspeccion.query.filter_by(actuacion_id=int(actuacion.id)).first()
    if inspeccion is None:
        return None
    row = (
        ActaInspeccionItem.query.filter_by(
            acta_inspeccion_id=int(inspeccion.id),
            item_acta_inspeccion_id=int(id_hab),
        )
        .limit(1)
        .first()
    )
    if row is None or row.valor_si_no is None:
        return None
    return bool(row.valor_si_no)


def _requested_efectivo_con_persistido(
    actuacion: Actuaciones,
    requested: list[dict[str, Any]],
    id_hab: int,
) -> list[dict[str, Any]]:
    """
    Combina ítems del payload con habilitación ya persistida si el PUT es parcial.
    No infiere respuesta cuando el payload envía lista vacía (limpieza explícita).
    """
    if not requested:
        return requested
    by_id = {int(r["item_id"]): dict(r) for r in requested}
    if id_hab not in by_id:
        persisted = _persisted_valor_si_no_habilitacion(actuacion, id_hab)
        if persisted is not None:
            by_id[id_hab] = {"item_id": id_hab, "valor_si_no": persisted}
    return list(by_id.values())


def exigir_tiene_habilitacion_inspeccion_real(actuacion: Actuaciones, payload: dict[str, Any]) -> bool:
    """
    True si se crea/modifica checklist de inspección real (sin contraproducencia operativa).

    Solo aplica cuando el payload incluye ``items_acta_inspeccion`` (no basta acta_inspeccion_num).
    Reinspección por notificación/oficio y ratificaciones quedan exentas.
    """
    if (actuacion.contraproducencia or "").strip():
        return False
    if actuacion.id and _circuito_exime_habilitacion(actuacion):
        return False
    if "items_acta_inspeccion" not in payload:
        return False
    inspeccion = Inspeccion.query.filter_by(actuacion_id=int(actuacion.id)).first()
    if inspeccion is None and not (payload.get("acta_inspeccion_num") or "").strip():
        return False
    return True


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
    effective = _requested_efectivo_con_persistido(actuacion, requested, id_hab)
    if _tiene_respuesta_habilitacion(effective, id_hab):
        return
    raise _validation_error_items_acta_inspeccion()
