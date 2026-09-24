"""Catálogo de ítems de checklist de acta de inspección."""

from __future__ import annotations

from typing import Any

from app.models import ItemActaInspeccion


def listar_items_acta_inspeccion_catalogo(*, solo_activos: bool = True) -> list[dict[str, Any]]:
    """
    Lista ítems del catálogo ordenados por ``orden``.

    Parámetros:
        solo_activos: si True, filtra ``activo=True`` (uso en dropdowns de alta).

    Retorno:
        Lista de dicts ``{id, codigo, nombre, orden, tipo_respuesta}`` (sin ``activo`` en API pública).
    """
    q = ItemActaInspeccion.query
    if solo_activos:
        q = q.filter(ItemActaInspeccion.activo.is_(True))
    rows = q.order_by(ItemActaInspeccion.orden.asc(), ItemActaInspeccion.id.asc()).all()
    return [
        {
            "id": int(r.id),
            "codigo": r.codigo,
            "nombre": r.nombre,
            "orden": int(r.orden),
            "tipo_respuesta": str(r.tipo_respuesta or "ESTADO"),
        }
        for r in rows
    ]
