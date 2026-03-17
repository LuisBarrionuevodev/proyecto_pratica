"""seed distritos from geojson with axis fix for mysql map

Revision ID: b3f1d9e8a7c6
Revises: a1f3c9e4d2b7
Create Date: 2026-03-17 18:20:00.000000

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3f1d9e8a7c6"
down_revision = "a1f3c9e4d2b7"
branch_labels = None
depends_on = None


def _geojson_path() -> Path:
    """
    Devuelve la ruta absoluta del GeoJSON canónico de distritos.
    """
    base_dir = Path(__file__).resolve().parents[2]
    return (base_dir / "app" / "domains" / "geolocalizacion" / "geocode" / "data" / "distritos.geojson").resolve()


def _ring_to_wkt(ring: list[Any]) -> str:
    """
    Convierte un anillo GeoJSON a coordenadas WKT cerradas.
    """
    points: list[str] = []
    for point in ring:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            lon = float(point[0])
            lat = float(point[1])
        except (TypeError, ValueError):
            continue
        points.append(f"{lon} {lat}")

    if len(points) < 3:
        return ""
    if points[0] != points[-1]:
        points.append(points[0])
    return ", ".join(points)


def _geometry_to_wkt(geometry: dict[str, Any]) -> str | None:
    """
    Convierte geometría GeoJSON (Polygon/MultiPolygon) a WKT POLYGON.
    """
    geo_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list):
        return None

    if geo_type == "Polygon":
        rings: list[str] = []
        for ring in coords:
            if not isinstance(ring, list):
                continue
            wkt_ring = _ring_to_wkt(ring)
            if wkt_ring:
                rings.append(f"({wkt_ring})")
        if not rings:
            return None
        return f"POLYGON ({', '.join(rings)})"

    if geo_type == "MultiPolygon":
        # Compatibilidad con esquema actual (distrito.geom = POLYGON).
        for polygon in coords:
            if not isinstance(polygon, list):
                continue
            rings: list[str] = []
            for ring in polygon:
                if not isinstance(ring, list):
                    continue
                wkt_ring = _ring_to_wkt(ring)
                if wkt_ring:
                    rings.append(f"({wkt_ring})")
            if rings:
                return f"POLYGON ({', '.join(rings)})"
    return None


def upgrade() -> None:
    """
    Seedea/actualiza la tabla distrito desde GeoJSON canónico del backend.

    Regla operativa:
    - Guarda geometría con ST_SwapXY(...) para corregir visualización en mapa MySQL.
    """
    geojson_file = _geojson_path()
    if not geojson_file.exists():
        raise ValueError(f"No existe el GeoJSON de distritos: {geojson_file}")

    data = json.loads(geojson_file.read_text(encoding="utf-8"))
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("GeoJSON inválido para distritos: falta lista 'features'.")

    conn = op.get_bind()
    upsert_sql = sa.text(
        """
        INSERT INTO distrito (nombre, geom)
        VALUES (:nombre, ST_SwapXY(ST_GeomFromText(:wkt, 4326)))
        ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre),
            geom = VALUES(geom)
        """
    )

    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        if not isinstance(props, dict) or not isinstance(geom, dict):
            continue

        nombre = str(props.get("nombre") or "").strip()
        wkt = _geometry_to_wkt(geom)
        if not nombre or not wkt:
            continue

        conn.execute(upsert_sql, {"nombre": nombre, "wkt": wkt})


def downgrade() -> None:
    """
    No aplica rollback de datos seed para distritos.
    """
    # Seed de datos operativos: downgrade intencionalmente sin cambios.
    return None

