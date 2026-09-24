from __future__ import annotations

from flask import Blueprint

geolocalizacion_geocode = Blueprint("geolocalizacion_geocode", __name__)

from . import geocode_one  # noqa: E402,F401
from . import geocode_pending  # noqa: E402,F401

__all__ = ["geolocalizacion_geocode"]
