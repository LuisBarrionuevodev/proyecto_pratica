"""
Consulta de ``map_points`` para Gestión Domicilios (PR6C.4).

Separado de filas paginadas: filtros por ``map_mode``, ``bbox`` y límite duro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import and_, case

from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_response import (
    GestionDomiciliosMapPointOut,
    GestionDomiciliosMapPointsMetaOut,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_status import (
    STATUS_LABELS,
    requiere_accion,
    resolve_status_operativo,
    status_operativo_sql_case,
)
from app.models import CalleCatalogo, Domicilio, DomicilioGeocode

if TYPE_CHECKING:
    from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_query import (
        GestionDomiciliosQuery,
        MapMode,
    )

MAP_POINTS_LIMIT = 200


@dataclass(frozen=True)
class Bbox:
    """Viewport geográfico min/max lat/lng."""

    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


def parse_bbox(bbox: str | None) -> Bbox | None:
    """
    Parsea ``bbox`` query param.

    Parámetros:
        bbox: ``min_lat,min_lng,max_lat,max_lng``.

    Retorno:
        ``Bbox`` o None si no se envió.

    Errores:
        ValueError: formato o rango inválido.
    """
    if bbox is None or not str(bbox).strip():
        return None
    parts = [p.strip() for p in str(bbox).split(",")]
    if len(parts) != 4:
        raise ValueError("bbox debe ser min_lat,min_lng,max_lat,max_lng")
    try:
        min_lat, min_lng, max_lat, max_lng = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError("bbox debe contener números válidos") from exc
    if min_lat > max_lat or min_lng > max_lng:
        raise ValueError("bbox inválido: min debe ser menor o igual que max")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("bbox: latitud fuera de rango")
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
        raise ValueError("bbox: longitud fuera de rango")
    return Bbox(min_lat=min_lat, min_lng=min_lng, max_lat=max_lat, max_lng=max_lng)


def _has_coords_filter():
    return and_(
        DomicilioGeocode.lat.isnot(None),
        DomicilioGeocode.lng.isnot(None),
    )


def _apply_bbox_filter(query, bbox: Bbox | None):
    if bbox is None:
        return query
    return query.filter(
        DomicilioGeocode.lat >= bbox.min_lat,
        DomicilioGeocode.lat <= bbox.max_lat,
        DomicilioGeocode.lng >= bbox.min_lng,
        DomicilioGeocode.lng <= bbox.max_lng,
    )


def _statuses_for_map_mode(map_mode: MapMode) -> list[str] | None:
    """
    Estados operativos incluidos por ``map_mode``.

    Retorno:
        Lista de statuses o None si no aplica filtro extra (``all``).
    """
    if map_mode == "all":
        return None
    if map_mode == "problematic":
        return ["punto_dudoso", "error"]
    if map_mode == "visible":
        return ["punto_dudoso", "manual", "geolocalizado"]
    if map_mode == "manual":
        return ["manual"]
    if map_mode == "errors":
        return ["error"]
    return None


def _apply_map_mode_filter(query, map_mode: MapMode):
    statuses = _statuses_for_map_mode(map_mode)
    if statuses is None:
        return query
    status_expr = status_operativo_sql_case()
    return query.filter(status_expr.in_(statuses))


def _format_domicilio_linea(dom: Domicilio) -> str:
    calle = (dom.calle_normalizada or dom.calle or "").strip()
    if (dom.numero_tipo or "").strip().upper() == "ESQUINA":
        esquina = (dom.esquina_normalizada or dom.esquina_raw or "").strip()
        if esquina and calle:
            return f"{calle} y {esquina}"
        return esquina or calle
    numero = (dom.numero or "").strip()
    if calle and numero:
        return f"{calle} {numero}"
    return calle or numero or f"Domicilio #{dom.id}"


def _map_points_order(query):
    """Prioriza casos que requieren acción antes del límite."""
    status_expr = status_operativo_sql_case()
    req_first = case(
        (status_expr.in_(["punto_dudoso", "error"]), 0),
        else_=1,
    )
    return query.order_by(req_first.asc(), Domicilio.updated_at.desc(), Domicilio.id.desc())


def fetch_map_points(
    *,
    base_query,
    query: GestionDomiciliosQuery,
) -> tuple[list[GestionDomiciliosMapPointOut], GestionDomiciliosMapPointsMetaOut]:
    """
    Obtiene puntos de mapa según filtros activos (sin paginación de tabla).

    Parámetros:
        base_query: query ya filtrada por ``q`` y ``status_operativo``.
        query: params completos (``map_mode``, ``bbox``).

    Retorno:
        Tupla (puntos, metadata de truncado/límite).
    """
    bbox = parse_bbox(query.bbox)
    q = _apply_map_mode_filter(base_query, query.map_mode)
    q = q.filter(_has_coords_filter())
    q = _apply_bbox_filter(q, bbox)

    total_matching = q.count()
    rows = _map_points_order(q).limit(MAP_POINTS_LIMIT).all()

    points: list[GestionDomiciliosMapPointOut] = []
    for dom, geo, _catalogo in rows:
        if geo is None or geo.lat is None or geo.lng is None:
            continue
        status = resolve_status_operativo(dom, geo)
        points.append(
            GestionDomiciliosMapPointOut(
                domicilio_id=int(dom.id),
                lat=float(geo.lat),
                lng=float(geo.lng),
                status_operativo=status,  # type: ignore[arg-type]
                status_operativo_label=STATUS_LABELS.get(status, status),
                label=_format_domicilio_linea(dom),
                geo_chip="EN_MAPA",
                requiere_accion=requiere_accion(status),
            )
        )

    meta = GestionDomiciliosMapPointsMetaOut(
        returned=len(points),
        limit=MAP_POINTS_LIMIT,
        truncated=total_matching > MAP_POINTS_LIMIT,
        total_matching=int(total_matching),
        map_mode=query.map_mode,
        bbox_applied=bbox is not None,
    )
    return points, meta
