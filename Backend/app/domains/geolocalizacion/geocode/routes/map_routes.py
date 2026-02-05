from __future__ import annotations

from flask import jsonify, request

from app.domains.geolocalizacion.geocode.services.map_service import (
    list_points,
    list_heatmap,
    list_distritos_metric,
    list_pendientes,
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
