from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.database import db
import sqlalchemy as sa
_DISTRICT_NUMBER_REGEX = re.compile(r"(\d+)")



def _normalize_name(value: str | None) -> str:
    """
    Normaliza nombres de distrito para matching idempotente.

    Args:
        value: nombre de distrito.

    Returns:
        Nombre normalizado en minúsculas y sin espacios duplicados.
    """
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _geojson_path() -> Path:
    """
    Resuelve la ruta absoluta del GeoJSON canónico de distritos.

    Returns:
        Ruta del archivo `distritos.geojson`.
    """
    return (Path(__file__).resolve().parent.parent / "data" / "distritos.geojson").resolve()


def _ring_to_wkt(ring: List[Any]) -> str:
    """
    Convierte un anillo GeoJSON a coordenadas WKT cerradas.
    """
    points: List[str] = []
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


def _geometry_to_wkt(geometry: Dict[str, Any]) -> str | None:
    """
    Convierte geometría GeoJSON (Polygon/MultiPolygon) a WKT POLYGON.
    """
    geo_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list):
        return None

    if geo_type == "Polygon":
        rings = []
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
        # La tabla actual es POLYGON. Para compatibilidad tomamos el primer polígono válido.
        for polygon in coords:
            if not isinstance(polygon, list):
                continue
            rings = []
            for ring in polygon:
                if not isinstance(ring, list):
                    continue
                wkt_ring = _ring_to_wkt(ring)
                if wkt_ring:
                    rings.append(f"({wkt_ring})")
            if rings:
                return f"POLYGON ({', '.join(rings)})"
    return None


def _extract_codigo(nombre: str) -> int | None:
    """
    Extrae código numérico de nombre de distrito.
    """
    match = _DISTRICT_NUMBER_REGEX.search(nombre or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _load_distritos_from_geojson(path: Path) -> List[Tuple[str, str, int | None]]:
    """
    Carga los nombres de distrito desde el GeoJSON canónico.

    Args:
        path: ruta del archivo GeoJSON.

    Returns:
        Lista `(nombre, geom_wkt, codigo)` por distrito.

    Raises:
        ValueError: si el archivo no tiene estructura GeoJSON esperada.
    """
    with path.open("r", encoding="utf-8") as file:
        data: Dict[str, Any] = json.load(file)

    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("GeoJSON invalido: 'features' no es una lista.")

    rows: List[Tuple[str, str, int | None]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            continue
        raw_name = props.get("nombre")
        if raw_name is None:
            continue
        name = str(raw_name).strip()
        geometry = feature.get("geometry") or {}
        if not isinstance(geometry, dict):
            continue
        geom_wkt = _geometry_to_wkt(geometry)
        if name and geom_wkt:
            rows.append((name, geom_wkt, _extract_codigo(name)))
    return rows


def seed_distritos_from_geojson(path: Path | None = None) -> Tuple[int, int, int]:
    """
    Seedea distritos en DB desde GeoJSON de forma idempotente.

    Args:
        path: ruta opcional del GeoJSON. Si no se envía, usa el canónico backend.

    Returns:
        Tupla `(created, updated, skipped)`.

    Raises:
        ValueError: si falta el archivo o si hay datos inválidos en GeoJSON.
    """
    geojson_path = (path or _geojson_path()).resolve()
    if not geojson_path.exists():
        raise ValueError(f"No existe GeoJSON de distritos: {geojson_path}")

    geojson_rows = _load_distritos_from_geojson(geojson_path)
    if not geojson_rows:
        raise ValueError("GeoJSON sin distritos validos para procesar.")

    created = 0
    updated = 0
    skipped = 0

    existing_rows = db.session.execute(
        sa.text("SELECT id, nombre FROM distrito")
    ).mappings().all()
    existing_by_norm: Dict[str, Tuple[int, str]] = {
        _normalize_name(str(row["nombre"])): (int(row["id"]), str(row["nombre"]))
        for row in existing_rows
        if _normalize_name(str(row["nombre"]))
    }

    upsert_sql = sa.text(
        """
        INSERT INTO distrito (nombre, codigo, geom)
        VALUES (:nombre, :codigo, ST_SwapXY(ST_GeomFromText(:wkt, 4326)))
        ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre),
            codigo = VALUES(codigo),
            geom = VALUES(geom)
        """
    )

    for geo_name, geo_wkt, geo_codigo in geojson_rows:
        key = _normalize_name(geo_name)
        if not key:
            skipped += 1
            continue

        existing = existing_by_norm.get(key)
        if existing is None:
            db.session.execute(
                upsert_sql,
                {"nombre": geo_name, "codigo": geo_codigo, "wkt": geo_wkt},
            )
            created += 1
            continue

        district_id, district_name = existing
        if district_name != geo_name:
            db.session.execute(
                sa.text(
                    """
                    UPDATE distrito
                    SET nombre = :nombre,
                        codigo = :codigo,
                        geom = ST_SwapXY(ST_GeomFromText(:wkt, 4326))
                    WHERE id = :district_id
                    """
                ),
                {
                    "nombre": geo_name,
                    "codigo": geo_codigo,
                    "wkt": geo_wkt,
                    "district_id": district_id,
                },
            )
            updated += 1
        else:
            skipped += 1

    db.session.commit()
    return created, updated, skipped


def _build_parser() -> argparse.ArgumentParser:
    """
    Crea parser CLI para seed de distritos.

    Returns:
        Parser de argumentos.
    """
    parser = argparse.ArgumentParser(description="Seed idempotente de Distrito desde GeoJSON.")
    parser.add_argument(
        "--path",
        required=False,
        help="Ruta opcional del GeoJSON de distritos. Por defecto usa el canónico backend.",
    )
    return parser


def main() -> None:
    """
    Punto de entrada CLI para ejecutar el seed de distritos.
    """
    parser = _build_parser()
    args = parser.parse_args()

    from app.main import create_app

    app = create_app()
    with app.app_context():
        path = Path(args.path).resolve() if args.path else None
        created, updated, skipped = seed_distritos_from_geojson(path=path)
        print(f"Seed Distrito OK. created={created} updated={updated} skipped={skipped}")


if __name__ == "__main__":
    main()
