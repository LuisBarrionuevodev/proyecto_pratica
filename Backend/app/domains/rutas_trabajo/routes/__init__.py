from __future__ import annotations

from flask import Blueprint

rutas_trabajo = Blueprint("rutas_trabajo", __name__)

# Registrar endpoints (side-effect imports)
from . import create_ruta  # noqa: E402,F401
from . import detail_ruta  # noqa: E402,F401
from . import create_grupo  # noqa: E402,F401
from . import replace_grupo_inspectores  # noqa: E402,F401
from . import list_iniciadores_pendientes  # noqa: E402,F401
from . import assign_items  # noqa: E402,F401
from . import move_item  # noqa: E402,F401
from . import delete_item  # noqa: E402,F401
from . import delete_grupo  # noqa: E402,F401
from . import patch_item_orden_trabajo  # noqa: E402,F401

__all__ = ["rutas_trabajo"]
