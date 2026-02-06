from __future__ import annotations

from flask import jsonify, request

from app.domains.geolocalizacion.geocode.services.map_service import (
    list_points,
    list_points_v2,
    list_heatmap,
    list_distritos_metric,
    list_pendientes,
    get_details,
)

from . import geolocalizacion_map


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
    )
    return jsonify({"items": items}), 200


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
