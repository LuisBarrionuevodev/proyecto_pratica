from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from app.models import Distrito


_CACHE: Optional[List[Dict[str, object]]] = None
_DISTRICT_MAP_CACHE: Optional[Dict[str, int]] = None

_EPSILON = 1e-9


def _normalize_name(value: str | None) -> str:
    """
    Normaliza nombres para matching canónico GeoJSON <-> DB.
    """
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _parse_ring(raw_ring: object) -> List[Tuple[float, float]]:
    """
    Parsea un anillo GeoJSON (lon,lat) ignorando puntos inválidos.
    """
    if not isinstance(raw_ring, list):
        return []
    ring: List[Tuple[float, float]] = []
    for point in raw_ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            x = float(point[0])
            y = float(point[1])
        except (TypeError, ValueError):
            continue
        ring.append((x, y))
    return ring


def _is_point_on_segment(
    point: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
    epsilon: float = _EPSILON,
) -> bool:
    """
    Evalúa si el punto está sobre el segmento AB (manejo de borde estable).
    """
    x, y = point
    x1, y1 = a
    x2, y2 = b

    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > epsilon:
        return False

    dot = (x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)
    if dot < -epsilon:
        return False

    sq_len = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if dot - sq_len > epsilon:
        return False
    return True


def _load_geojson() -> List[Dict[str, object]]:
    """
    Carga y parsea distritos.geojson desde backend (fuente canónica).
    """
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
        try:
            props = feat.get("properties") or {}
            nombre = (props.get("nombre") or "").strip()
            geom = feat.get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates") or []
            polygons: List[List[List[Tuple[float, float]]]] = []

            if gtype == "Polygon":
                rings = [_parse_ring(ring) for ring in coords if isinstance(ring, list)]
                if rings:
                    polygons = [rings]
            elif gtype == "MultiPolygon":
                for poly in coords:
                    if not isinstance(poly, list):
                        continue
                    rings = [_parse_ring(ring) for ring in poly if isinstance(ring, list)]
                    if rings:
                        polygons.append(rings)

            parsed.append(
                {
                    "nombre": nombre,
                    "nombre_norm": _normalize_name(nombre),
                    "polygons": polygons,
                }
            )
        except Exception:
            # Feature inválida: se omite, sin romper resolución completa.
            continue

    _CACHE = parsed
    return parsed


def _point_in_ring(point: Tuple[float, float], ring: List[Tuple[float, float]]) -> bool:
    """
    Ray-casting para anillo; incluye borde como "dentro" de forma estable.
    """
    x, y = point
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if _is_point_on_segment(point, (xi, yi), (xj, yj)):
            return True
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(point: Tuple[float, float], polygon: List[List[Tuple[float, float]]]) -> bool:
    """
    Evalúa punto en polígono (outer - holes).
    """
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


def _load_district_name_map() -> Dict[str, int]:
    """
    Mapa canónico nombre_normalizado -> distrito_id desde tabla Distrito.
    """
    global _DISTRICT_MAP_CACHE
    if _DISTRICT_MAP_CACHE is not None:
        return _DISTRICT_MAP_CACHE

    mapping: Dict[str, int] = {}
    rows = Distrito.query.with_entities(Distrito.id, Distrito.nombre).all()
    for district_id, district_name in rows:
        key = _normalize_name(district_name)
        if key and key not in mapping:
            mapping[key] = int(district_id)
    _DISTRICT_MAP_CACHE = mapping
    return mapping


def resolve_distrito_id(lat: float, lon: float) -> Optional[int]:
    """
    Resuelve distrito por point-in-polygon usando GeoJSON de distritos.

    Args:
        lat: latitud
        lon: longitud

    Returns:
        distrito_id o None si no encuentra.
    """
    point = (float(lon), float(lat))
    district_by_name = _load_district_name_map()

    for item in _load_geojson():
        nombre_norm = str(item.get("nombre_norm") or "")
        polygons = item.get("polygons") or []
        for poly in polygons:
            try:
                if _point_in_polygon(point, poly):
                    if not nombre_norm:
                        return None
                    return district_by_name.get(nombre_norm)
            except Exception:
                # Polígono inválido: se ignora y continúa con el resto.
                continue
    return None
