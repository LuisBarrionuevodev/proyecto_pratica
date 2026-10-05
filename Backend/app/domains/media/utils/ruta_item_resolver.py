"""Resolución de RutaItem desde actuación (detalle Gestión / media)."""

from __future__ import annotations

from app.models import RutaItem


def resolve_ruta_item_id_for_actuacion(actuacion_id: int) -> int | None:
    """
    Obtiene el ítem de ruta operativo más reciente vinculado a una actuación.

    Parámetros:
        actuacion_id: PK de actuación.

    Retorno:
        id de ``RutaItem`` o ``None`` si no hay vínculo.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(actuacion_id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None:
        return None
    return int(item.id)


def resolve_observaciones_ejecucion_for_actuacion(actuacion_id: int) -> str | None:
    """
    Texto de observaciones de ejecución del ítem de ruta vinculado a la actuación.

    Parámetros:
        actuacion_id: PK de actuación.

    Retorno:
        Texto recortado o ``None`` si no hay vínculo o el campo está vacío.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(actuacion_id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None or item.observaciones_ejecucion is None:
        return None
    s = str(item.observaciones_ejecucion).strip()
    return s or None
