from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func

from app.models import Distrito


_CACHE: Optional[List[Dict[str, object]]] = None


def _load_geojson() -> List[Dict[str, object]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "..", "data", "distritos.geojson")
    path = os.path.abspath(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features") or []
    parsed: List[Dict[str, object]] = []
    for feat in features:
        props = feat.get("properties") or {}
        nombre = (props.get("nombre") or "").strip()
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates") or []
        polygons: List[List[List[Tuple[float, float]]]] = []

        if gtype == "Polygon":
            polygons = [[[(p[0], p[1]) for p in ring] for ring in coords]]
        elif gtype == "MultiPolygon":
            polygons = [
                [[(p[0], p[1]) for p in ring] for ring in poly] for poly in coords
            ]
        else:
            polygons = []

        parsed.append({"nombre": nombre, "polygons": polygons})

    _CACHE = parsed
    return parsed


def _point_in_ring(point: Tuple[float, float], ring: List[Tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(point: Tuple[float, float], polygon: List[List[Tuple[float, float]]]) -> bool:
    if not polygon:
        return False
    outer = polygon[0]
    if not _point_in_ring(point, outer):
        return False
    # holes
    for hole in polygon[1:]:
        if _point_in_ring(point, hole):
            return False
    return True


def resolve_distrito_id(lat: float, lon: float) -> Optional[int]:
    """
    Resuelve distrito por point-in-polygon usando GeoJSON de distritos.

    Args:
        lat: latitud
        lon: longitud

    Returns:
        distrito_id o None si no encuentra.
    """
    point = (lon, lat)
    for item in _load_geojson():
        nombre = item.get("nombre")
        polygons = item.get("polygons") or []
        for poly in polygons:
            if _point_in_polygon(point, poly):
                if not nombre:
                    return None
                distrito = (
                    Distrito.query.filter(func.lower(Distrito.nombre) == str(nombre).lower())
                    .first()
                )
                return distrito.id if distrito else None
    return None
