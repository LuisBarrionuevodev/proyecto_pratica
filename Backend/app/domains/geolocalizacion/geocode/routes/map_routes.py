from __future__ import annotations

import re

from flask import Response, jsonify, request

from app.domains.geolocalizacion.geocode.services.map_service import (
    list_points,
    list_points_v2,
    list_heatmap,
    list_distritos_metric,
    list_pendientes,
    get_details,
    save_manual_geocode,
)

from app.domains.geolocalizacion.geocode.services.osm_static_map_proxy_service import (
    fetch_osm_static_map_bytes,
)

from . import geolocalizacion_map

_CENTER_RE = re.compile(r"^-?\d{1,3}(\.\d+)?,-?\d{1,3}(\.\d+)?$")
_SIZE_RE = re.compile(r"^(\d{1,4})x(\d{1,4})$")
_MARKERS_RE = re.compile(r"^[\d.,|a-zA-Z-]+$")
_MAX_MARKERS_LEN = 4000


@geolocalizacion_map.get("/map/osm-static")
def map_osm_static():
    """
    Proxy acotado hacia staticmap.openstreetmap.de para embeber mini-mapas en PDFs.

    El navegador no puede leer la imagen OSM con fetch directo (CORS); el backend
    reenvía la petición con los mismos parámetros tras validarlos.

    Query: center, zoom, size, maptype, markers (opcional), mismos nombres que OSM.

    Returns:
        Imagen PNG (bytes) o JSON de error 4xx/502.
    """
    center = (request.args.get("center") or "").strip()
    zoom_s = (request.args.get("zoom") or "14").strip()
    size = (request.args.get("size") or "520x280").strip()
    maptype = (request.args.get("maptype") or "mapnik").strip().lower()
    markers = request.args.get("markers")

    if not _CENTER_RE.fullmatch(center):
        return jsonify({"detail": "Parámetro center inválido (se espera lat,lng)."}), 400
    try:
        zoom = int(zoom_s)
    except ValueError:
        return jsonify({"detail": "zoom debe ser entero."}), 400
    if zoom < 10 or zoom > 18:
        return jsonify({"detail": "zoom fuera de rango permitido (10–18)."}), 400

    m = _SIZE_RE.match(size)
    if not m:
        return jsonify({"detail": "size inválido (ej. 520x280)."}), 400
    w, h = int(m.group(1)), int(m.group(2))
    if w < 50 or h < 50 or w > 800 or h > 800:
        return jsonify({"detail": "dimensiones de size fuera de rango (50–800)."}), 400

    if maptype != "mapnik":
        return jsonify({"detail": "maptype no permitido."}), 400

    markers_arg: str | None = None
    if markers is not None:
        markers = markers.strip()
        if len(markers) > _MAX_MARKERS_LEN:
            return jsonify({"detail": "markers demasiado largo."}), 400
        if not _MARKERS_RE.fullmatch(markers):
            return jsonify({"detail": "markers con caracteres no permitidos."}), 400
        markers_arg = markers

    payload = fetch_osm_static_map_bytes(center, zoom, size, markers_arg)
    if payload[0] is None:
        _, err = payload
        return (
            jsonify(
                {
                    "detail": "Servicio de mapa estático no devolvió imagen tras reintentos.",
                    "hint": err[:240],
                }
            ),
            502,
        )

    body, ctype = payload
    return Response(body, mimetype=ctype, status=200)


@geolocalizacion_map.get("/map/puntos")
def map_puntos():
    """
    Devuelve GeoJSON de puntos geocodificados.
    """
    params = request.args.to_dict()
    items = list_points(
        desde=params.get("desde"),
        hasta=params.get("hasta"),
        tipo=params.get("tipo"),
        rubro=params.get("rubro"),
        distrito_id=int(params["distrito_id"]) if params.get("distrito_id") else None,
    )
    features = []
    for item in items:
        if item.get("lat") is None or item.get("lng") is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [item["lng"], item["lat"]]},
                "properties": {k: v for k, v in item.items() if k not in {"lat", "lng"}},
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features}), 200


@geolocalizacion_map.get("/map/points")
def map_points():
    """
    Puntos agregados por domicilio con filtros.

    Returns:
        FeatureCollection.
    """
    params = request.args.to_dict()
    items = list_points_v2(
        desde=params.get("from") or params.get("desde"),
        hasta=params.get("to") or params.get("hasta"),
        origin=None if params.get("origin") in {None, "", "all"} else params.get("origin"),
        tipo=params.get("tipo"),
        contraproducencia=params.get("contraproducencia"),
        rubro_id=int(params["rubro_id"]) if params.get("rubro_id") else None,
        distrito_id=int(params["distrito_id"]) if params.get("distrito_id") else None,
    )
    features = []
    for item in items:
        if item.get("lat") is None or item.get("lng") is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [item["lng"], item["lat"]]},
                "properties": {k: v for k, v in item.items() if k not in {"lat", "lng"}},
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features}), 200


@geolocalizacion_map.get("/map/heatmap")
def map_heatmap():
    """
    Devuelve lista de puntos para heatmap.
    """
    params = request.args.to_dict()
    items = list_heatmap(
        desde=params.get("desde"),
        hasta=params.get("hasta"),
        tipo=params.get("tipo"),
        rubro=params.get("rubro"),
        distrito_id=int(params["distrito_id"]) if params.get("distrito_id") else None,
        metrica=params.get("metrica"),
    )
    return jsonify({"items": items}), 200


@geolocalizacion_map.get("/map/distritos")
def map_distritos():
    """
    Devuelve valores por distrito (sin geometría).
    """
    params = request.args.to_dict()
    items = list_distritos_metric(
        desde=params.get("desde"),
        hasta=params.get("hasta"),
        tipo=params.get("tipo"),
        rubro=params.get("rubro"),
    )
    return jsonify({"items": items}), 200


@geolocalizacion_map.get("/map/pendientes")
def map_pendientes():
    """
    Devuelve domicilios pendientes de geocoding/normalización.
    """
    params = request.args.to_dict()
    items = list_pendientes(
        desde=params.get("desde"),
        hasta=params.get("hasta"),
        scope=params.get("scope"),
        kind=params.get("kind"),
    )
    return jsonify({"items": items}), 200


@geolocalizacion_map.get("/api/map/pendientes")
def map_pendientes_alias():
    """
    Alias para pendientes con prefijo /api.
    """
    return map_pendientes()


@geolocalizacion_map.post("/api/map/geocode/manual")
def map_geocode_manual():
    """
    Guarda un punto manual desde el mapa.
    """
    payload = request.get_json(silent=True) or {}
    domicilio_id = payload.get("domicilio_id")
    lat = payload.get("lat")
    lng = payload.get("lng")
    do_reverse = bool(payload.get("do_reverse", False))
    if domicilio_id is None or lat is None or lng is None:
        return jsonify({"detail": "domicilio_id, lat y lng son obligatorios"}), 400
    try:
        result = save_manual_geocode(
            domicilio_id=int(domicilio_id),
            lat=float(lat),
            lng=float(lng),
            do_reverse=do_reverse,
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 404
    except Exception as exc:
        return jsonify({"detail": "Error interno", "error": str(exc)}), 500


@geolocalizacion_map.get("/map/details/<int:domicilio_id>")
def map_details(domicilio_id: int):
    """
    Detalle de domicilio para card del mapa.

    Args:
        domicilio_id: id del domicilio.

    Returns:
        Detalle agregado de actuaciones y relevamientos.
    """
    params = request.args.to_dict()
    try:
        data = get_details(
            domicilio_id=domicilio_id,
            desde=params.get("from") or params.get("desde"),
            hasta=params.get("to") or params.get("hasta"),
        )
        return jsonify(data), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 404
    except Exception as e:
        return jsonify({"detail": "Error interno", "error": str(e)}), 500
