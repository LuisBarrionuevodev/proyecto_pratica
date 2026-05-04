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
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    list_mapa_operativo_pendientes_geo,
    list_mapa_operativo_realizados_geo,
)

from app.domains.geolocalizacion.geocode.services.osm_static_map_proxy_service import (
    fetch_osm_static_map_bytes,
)

from . import geolocalizacion_map

_CENTER_RE = re.compile(r"^-?\d{1,3}(\.\d+)?,-?\d{1,3}(\.\d+)?$")
_SIZE_RE = re.compile(r"^(\d{1,4})x(\d{1,4})$")
_MARKERS_RE = re.compile(r"^[\d.,|a-zA-Z-]+$")
_MAX_MARKERS_LEN = 4000
_PIN_LBL_MAX_LEN = 2000
_PIN_LBL_SEG_MAX = 48


def _pin_lbl_valid_for_markers(pin_lbl: str, marker_segment_count: int) -> bool:
    """
    Valida ``pin_lbl`` (segmentos ``|``): misma cantidad que marcadores, texto imprimible acotado.
    """
    if marker_segment_count <= 0 or not pin_lbl:
        return False
    if len(pin_lbl) > _PIN_LBL_MAX_LEN:
        return False
    parts = pin_lbl.split("|")
    if len(parts) != marker_segment_count:
        return False
    for p in parts:
        if len(p) > _PIN_LBL_SEG_MAX:
            return False
        for ch in p:
            o = ord(ch)
            if o < 32 or o == 127:
                return False
    return True


@geolocalizacion_map.get("/map/osm-static")
def map_osm_static():
    """
    Proxy acotado hacia staticmap.openstreetmap.de para embeber mini-mapas en PDFs.

    El navegador no puede leer la imagen OSM con fetch directo (CORS); el backend
    reenvía la petición con los mismos parámetros tras validarlos.

    Query: center, zoom, size, maptype, markers (opcional), mismos nombres que OSM.
    Opcional para el PDF (fallback teselas): pin_g y pin_o (segmentos ``|`` alineados con markers:
    grupo 1-based y orden de visita en el grupo). Opcional pin_lbl (mismos segmentos): leyenda por pin
    para polilínea y etiqueta en el mapa por teselas.

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

    pin_g = (request.args.get("pin_g") or "").strip() or None
    pin_o = (request.args.get("pin_o") or "").strip() or None
    pin_lbl_raw = request.args.get("pin_lbl")
    pin_lbl = (pin_lbl_raw or "").strip() or None if pin_lbl_raw is not None else None
    if pin_g and not re.fullmatch(r"[\d|]+", pin_g):
        pin_g, pin_o = None, None
    elif pin_o and not re.fullmatch(r"[\d|]+", pin_o):
        pin_g, pin_o = None, None
    elif markers_arg and pin_g and pin_o:
        mc = len([p for p in markers_arg.split("|") if p.strip()])
        pg = len([p for p in pin_g.split("|") if p.strip()])
        po = len([p for p in pin_o.split("|") if p.strip()])
        if pg != mc or po != mc:
            pin_g, pin_o = None, None
        elif pin_lbl and not _pin_lbl_valid_for_markers(pin_lbl, mc):
            pin_lbl = None
    else:
        pin_lbl = None

    if not (markers_arg and pin_g and pin_o):
        pin_lbl = None

    payload = fetch_osm_static_map_bytes(
        center, zoom, size, markers_arg, pin_g=pin_g, pin_o=pin_o, pin_lbl=pin_lbl
    )
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


def _fc_from_points(items: list[dict]) -> tuple[dict, int]:
    """Arma FeatureCollection HTTP 200 o JSON de error."""
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
    return {"type": "FeatureCollection", "features": features}, 200


@geolocalizacion_map.get("/map/operativo/pendientes")
def map_operativo_pendientes():
    """
    Mapa operativo — pendientes: cola de iniciadores + ítems EN_PROCESO (ruta publicada).

    Query: desde, hasta (ISO date), opcional distrito_id, tipo (filtro UI), inspector_id.
    """
    params = request.args.to_dict()
    distrito_id = int(params["distrito_id"]) if params.get("distrito_id") else None
    inspector_id = int(params["inspector_id"]) if params.get("inspector_id") else None
    try:
        items = list_mapa_operativo_pendientes_geo(
            desde=params.get("desde") or params.get("from"),
            hasta=params.get("hasta") or params.get("to"),
            distrito_id=distrito_id,
            tipo=params.get("tipo"),
            inspector_id=inspector_id,
        )
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400
    body, status = _fc_from_points(items)
    return jsonify(body), status


@geolocalizacion_map.get("/api/map/operativo/pendientes")
def map_operativo_pendientes_alias():
    return map_operativo_pendientes()


@geolocalizacion_map.get("/map/operativo/realizados")
def map_operativo_realizados():
    """
    Mapa operativo — realizados: ``RutaItem`` finalizado con visita realizada en el rango.

    Query opcional: ``definicion`` (``TODOS``, ``CLAUSURA``, ``DECOMISO``, ``CLAUSURA_DECOMISO``).
    """
    params = request.args.to_dict()
    distrito_id = int(params["distrito_id"]) if params.get("distrito_id") else None
    inspector_id = int(params["inspector_id"]) if params.get("inspector_id") else None
    try:
        items = list_mapa_operativo_realizados_geo(
            desde=params.get("desde") or params.get("from"),
            hasta=params.get("hasta") or params.get("to"),
            distrito_id=distrito_id,
            tipo=params.get("tipo"),
            inspector_id=inspector_id,
            definicion=params.get("definicion"),
        )
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400
    body, status = _fc_from_points(items)
    return jsonify(body), status


@geolocalizacion_map.get("/api/map/operativo/realizados")
def map_operativo_realizados_alias():
    return map_operativo_realizados()


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
