from __future__ import annotations

from typing import List, Dict, Optional

from app.domains.geolocalizacion.normalizacion_calles.repos.calle_catalogo_repo import search_catalogo


def listar_catalogo_calles(search: Optional[str], limit: int = 20) -> List[Dict[str, object]]:
    """
    Lista calles del catálogo activas filtrando por búsqueda.
    """
    rows = search_catalogo(search, limit=limit)
    return [{"id": r[0], "nombre": r[1]} for r in rows]
