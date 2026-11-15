"""Mapper de vinculación: fingerprint y serialización (sin DB writes)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models import Contribuyente


def contribuyente_publico_dict(contrib: Contribuyente | None) -> dict[str, Any] | None:
    """Datos de titular para preview (no incluye campos internos)."""
    if contrib is None:
        return None
    return {
        "id": int(contrib.id),
        "documento": contrib.documento,
        "apellido": contrib.apellido,
        "nombre": contrib.nombre,
        "razon_social": contrib.razon_social,
    }


def fingerprint_vinculacion(
    *,
    establecimiento_id: int,
    origen_id: int,
    destino_id: int,
    domicilio_ids: list[int],
    lookalike_ids: list[int],
) -> str:
    """
    Token de alcance para detectar cambios entre preview y confirmación.

    Parámetros:
        establecimiento_id, origen_id, destino_id: ids comprobados.
        domicilio_ids: domicilios de la ficha lógica.
        lookalike_ids: filas ambiguas (deben permanecer iguales).

    Retorno:
        Hex SHA-256 estable.
    """
    payload = {
        "eo": int(establecimiento_id),
        "origen": int(origen_id),
        "destino": int(destino_id),
        "doms": sorted(int(i) for i in domicilio_ids),
        "look": sorted(int(i) for i in lookalike_ids),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
