"""
Campos de estrategia de match para Gestión Domicilios (PR6A.1).

Solo lectura / presentación: no altera reglas de ``match_calle``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.domains.geolocalizacion.normalizacion_calles.services.match_calle_service import (
    match_calle,
)
from app.models import Domicilio


@lru_cache(maxsize=1024)
def _match_meta_for_calle(calle: str) -> tuple[str | None, str | None]:
    """Cache en memoria por texto de calle (solo presentación)."""
    result = match_calle(calle)
    return (result.get("match_strategy"), result.get("confidence_reason"))


def nomenclatura_match_fields(domicilio: Domicilio) -> dict[str, Any]:
    """
    Expone ``match_strategy`` y ``confidence_reason`` opcionales para filas de gestión.

    Parámetros:
        domicilio: instancia ORM con ``calle`` cargada.

    Retorno:
        Dict vacío o con claves opcionales ``match_strategy`` y ``confidence_reason``.
        Si el domicilio no tiene calle, retorna dict vacío.
    """
    stored_strategy = getattr(domicilio, "calle_match_strategy", None)
    stored_reason = getattr(domicilio, "calle_confidence_reason", None)
    if stored_strategy is not None:
        return {
            "match_strategy": stored_strategy,
            "confidence_reason": stored_reason,
        }

    calle = (domicilio.calle or "").strip()
    if not calle:
        return {}

    strategy, reason = _match_meta_for_calle(calle)
    if strategy is None and reason is None:
        return {}
    return {
        "match_strategy": strategy,
        "confidence_reason": reason,
    }
