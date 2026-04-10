"""
Resolución de inspectores del grupo de ruta para cierre de Completar trabajo.

Si el cliente no envía la lista explícita, el backend completa con los nombres del catálogo
asociados al ``RutaGrupo`` del ítem (misma fuente que al armar la ruta).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.models import RutaItem


def list_inspector_nombres_desde_ruta_item_grupo(item: "RutaItem") -> List[str]:
    """
    Devuelve los nombres de inspectores del grupo de la ruta del ítem, en orden estable.

    Orden: por ``RutaGrupoInspector.id`` ascendente. Sin duplicados por ``inspector_id``.

    Parámetros:
        item: ``RutaItem`` con ``ruta_grupo`` y ``grupo_inspectores`` / ``inspector`` cargados.

    Returns:
        Lista de strings (``Inspector.nombre``) listos para ``get_inspectores_o_falla``.
        Vacía si no hay grupo o no hay inspectores vinculados.
    """
    grupo = getattr(item, "ruta_grupo", None)
    if grupo is None:
        return []

    links = list(getattr(grupo, "grupo_inspectores", None) or [])
    links.sort(key=lambda x: int(getattr(x, "id", 0) or 0))

    seen_ids: set[int] = set()
    nombres: List[str] = []
    for link in links:
        ins = getattr(link, "inspector", None)
        if ins is None:
            continue
        iid = getattr(ins, "id", None)
        if iid is None or int(iid) in seen_ids:
            continue
        seen_ids.add(int(iid))
        raw = getattr(ins, "nombre", None)
        name = str(raw).strip() if raw is not None else ""
        if name:
            nombres.append(name)
    return nombres
