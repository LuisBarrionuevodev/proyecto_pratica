from __future__ import annotations

from flask import Blueprint

geolocalizacion_calles = Blueprint("geolocalizacion_calles", __name__)

from . import normalize_one  # noqa: E402,F401
from . import normalize_pending  # noqa: E402,F401
from . import catalogo_list  # noqa: E402,F401
from . import distrito_catalogo_list  # noqa: E402,F401
from . import set_canon  # noqa: E402,F401
from . import set_numero  # noqa: E402,F401
from . import guardar_nomenclatura  # noqa: E402,F401

__all__ = ["geolocalizacion_calles"]
