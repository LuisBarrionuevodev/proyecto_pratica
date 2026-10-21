"""Coerción de ítems de checklist entre JSON, Pydantic y payload canónico."""

from __future__ import annotations

from typing import Any

from app.domains.actuaciones.schemas.item_acta_inspeccion_estado_in import (
    ItemActaInspeccionEstadoIn,
)


def coerce_item_acta_inspeccion_estado(raw: Any) -> ItemActaInspeccionEstadoIn:
    """
    Convierte un ítem de checklist a ``ItemActaInspeccionEstadoIn``.

    Parámetros:
        raw: instancia validada, dict JSON o objeto compatible con ``model_validate``.

    Retorno:
        Modelo tipado listo para mapper/servicios.

    Errores esperados:
        ValidationError (Pydantic) si el dato es inválido.
        ValueError si el tipo no es reconocible.
    """
    if isinstance(raw, ItemActaInspeccionEstadoIn):
        return raw
    if isinstance(raw, dict):
        return ItemActaInspeccionEstadoIn.model_validate(raw)
    raise ValueError(
        "items_acta_inspeccion debe contener objetos con item_id y estado o valor_si_no."
    )


def item_acta_inspeccion_estado_to_payload_dict(
    item: ItemActaInspeccionEstadoIn,
) -> dict[str, Any]:
    """
    Dict canónico para ``aplicar_inspeccion_checklist_desde_payload`` / attach.

    Parámetros:
        item: ítem validado.

    Retorno:
        ``{"item_id", "estado"? , "valor_si_no"?}`` con una sola variante de respuesta.
    """
    out: dict[str, Any] = {"item_id": int(item.item_id)}
    if item.estado is not None:
        out["estado"] = str(item.estado)
    if item.valor_si_no is not None:
        out["valor_si_no"] = bool(item.valor_si_no)
    return out


def coerce_items_acta_inspeccion_list(raw_items: Any) -> list[ItemActaInspeccionEstadoIn]:
    """
    Normaliza una lista heterogénea (dict / modelo) a modelos tipados.

    Parámetros:
        raw_items: lista o None.

    Retorno:
        Lista de ``ItemActaInspeccionEstadoIn``.

    Errores esperados:
        ValueError si no es lista; ValidationError por ítem inválido.
    """
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise ValueError("items_acta_inspeccion debe ser una lista.")
    return [coerce_item_acta_inspeccion_estado(raw) for raw in raw_items]
