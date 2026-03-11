from __future__ import annotations

from flask import Blueprint

actuacion = Blueprint("actuaciones", __name__)

# Registrar endpoints (side-effect imports)
from . import create  # noqa: E402,F401
from . import update  # noqa: E402,F401
from . import delete  # noqa: E402,F401
from . import list  # noqa: E402,F401
from . import pendientes_vinc_acta  # noqa: E402,F401
from . import expediente_from_acta  # noqa: E402,F401
from . import pendientes_vinc_oficio  # noqa: E402,F401
from . import pendientes_notificacion  # noqa: E402,F401
from . import pendientes  # noqa: E402,F401
from . import pendientes_expediente  # noqa: E402,F401
from . import pendientes_oficio  # noqa: E402,F401
from . import oficio_from_acta  # noqa: E402,F401

__all__ = ["actuacion"]
