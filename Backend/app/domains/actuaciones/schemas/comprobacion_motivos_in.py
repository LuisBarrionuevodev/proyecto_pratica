from __future__ import annotations

from typing import Any, Optional

from app.domains.actuaciones.schemas.list_filters import _clean_str, _coerce_catalog_value
from app.models import CatalogMotivoComprobacion

_MSG_LISTA = "motivos_comprobacion debe ser una lista."
_MSG_DUPLICADO = "El mismo motivo de comprobación no puede repetirse."


def parse_lista_motivos_comprobacion(v: Any) -> Optional[list[str]]:
    """
    Normaliza `motivos_comprobacion` a nombres canónicos de catálogo, sin duplicados.

    Parámetros:
        v: None, lista de strings, o un string único.

    Returns:
        Lista de nombres canónicos, lista vacía, o None si `v` es None.

    Errores:
        ValueError: tipo inválido, duplicado o nombre ausente del catálogo.
    """
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        items: list[Any] = [s] if s else []
    elif isinstance(v, list):
        items = v
    else:
        raise ValueError(_MSG_LISTA)
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        s = _clean_str(raw)
        if not s:
            continue
        nombre = _coerce_catalog_value(s, CatalogMotivoComprobacion, "motivo de comprobación")
        if not nombre:
            raise ValueError(f"Motivo de comprobación no existe en catálogo: {s}")
        if nombre in seen:
            raise ValueError(_MSG_DUPLICADO)
        seen.add(nombre)
        out.append(nombre)
    return out


def motivos_comprobacion_efectivos(
    *,
    motivos_comprobacion: Optional[list[str]],
    comprobacion_motivo: Optional[str],
    fields_set: set[str],
) -> list[str]:
    """
    Resuelve la lista a persistir: el arreglo nuevo gana sobre el escalar legado.

    Parámetros:
        motivos_comprobacion: lista ya normalizada o None.
        comprobacion_motivo: texto legado opcional.
        fields_set: `model_fields_set` del schema.

    Returns:
        Nombres en orden. Vacío si no hay motivos enviados.
    """
    if "motivos_comprobacion" in fields_set and motivos_comprobacion is not None:
        return list(motivos_comprobacion)
    s = (comprobacion_motivo or "").strip()
    if s:
        return [s]
    return []
