from __future__ import annotations

from flask import Blueprint

geolocalizacion_map = Blueprint("geolocalizacion_map", __name__)

from . import map_routes  # noqa: E402,F401

__all__ = ["geolocalizacion_map"]
