from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.database import db


def resolve_distrito_id(lat: float, lon: float) -> Optional[int]:
    """
    Resuelve distrito por validación espacial contra `distrito.geom` en DB.

    Args:
        lat: latitud del punto.
        lon: longitud del punto.

    Returns:
        ID de distrito o None si no hay match.

    Errors:
        Propaga excepción técnica de DB para que el caller la registre como `district_error`.
    """
    lat_f = float(lat)
    lon_f = float(lon)
    point_wkt = f"POINT({lon_f} {lat_f})"

    contains_sql = sa.text(
        """
        SELECT d.id
        FROM distrito d
        WHERE d.geom IS NOT NULL
          AND ST_Contains(ST_SwapXY(d.geom), ST_GeomFromText(:point_wkt, 4326))
        LIMIT 1
        """
    )
    row = db.session.execute(contains_sql, {"point_wkt": point_wkt}).fetchone()
    if row:
        return int(row[0])

    # Fallback para puntos sobre borde geométrico.
    intersects_sql = sa.text(
        """
        SELECT d.id
        FROM distrito d
        WHERE d.geom IS NOT NULL
          AND ST_Intersects(ST_SwapXY(d.geom), ST_GeomFromText(:point_wkt, 4326))
        LIMIT 1
        """
    )
    row = db.session.execute(intersects_sql, {"point_wkt": point_wkt}).fetchone()
    if row:
        return int(row[0])

    return None
