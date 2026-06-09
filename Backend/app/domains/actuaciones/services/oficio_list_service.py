from __future__ import annotations

from typing import Any

from app.models import Oficio


def list_oficios_by_comprobacion(comprobacion_id: int) -> list[Oficio]:
    """
    Lista oficios activos asociados a una comprobación.

    Parámetros:
        comprobacion_id: FK de comprobación.

    Retorno:
        Lista ordenada por ``id`` ascendente (estable para UI legacy = primer oficio).

    Errores esperados:
        Ninguno; devuelve lista vacía si no hay oficios.
    """
    return (
        Oficio.query.filter_by(comprobacion_id=int(comprobacion_id))
        .filter(Oficio.deleted_at.is_(None))
        .order_by(Oficio.id.asc())
        .all()
    )


def oficios_comprobacion_payload(comprobacion_id: int) -> list[dict[str, Any]]:
    """
    Serializa oficios activos de una comprobación para API interna/PR4.

    Parámetros:
        comprobacion_id: FK de comprobación.

    Retorno:
        Lista de dicts con campos básicos del oficio (sin relaciones pesadas).
    """
    return [oficio.to_dict() for oficio in list_oficios_by_comprobacion(comprobacion_id)]
