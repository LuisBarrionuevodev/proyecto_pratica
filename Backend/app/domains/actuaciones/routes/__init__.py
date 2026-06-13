from __future__ import annotations

from flask import Blueprint

actuacion = Blueprint("actuaciones", __name__)

# Registrar endpoints (side-effect imports)
from . import create  # noqa: E402,F401
from . import update  # noqa: E402,F401
from . import delete  # noqa: E402,F401
from . import list  # noqa: E402,F401
from . import search  # noqa: E402,F401
from . import pendientes_vinc_acta  # noqa: E402,F401
from . import expediente_from_acta  # noqa: E402,F401
from . import pendientes_vinc_oficio  # noqa: E402,F401
from . import pendientes_notificacion  # noqa: E402,F401
from . import pendientes  # noqa: E402,F401
from . import pendientes_sync_notificaciones_vencidas  # noqa: E402,F401
from . import pendientes_expediente  # noqa: E402,F401
from . import notificacion_prorroga_expedientes  # noqa: E402,F401
from . import notificacion_plazo_expediente_edit  # noqa: E402,F401
from . import pendientes_oficio  # noqa: E402,F401
from . import comprobacion_actas  # noqa: E402,F401
from . import comprobacion_documental  # noqa: E402,F401
from . import oficio_from_acta  # noqa: E402,F401
from . import list_oficios_comprobacion  # noqa: E402,F401
from . import completar_trabajo_pendientes  # noqa: E402,F401
from . import completar_trabajo_pendientes_resumen  # noqa: E402,F401
from . import completar_trabajo_cerrar  # noqa: E402,F401
from . import completar_trabajo_detalle  # noqa: E402,F401
from . import epicollect_import  # noqa: E402,F401
from . import actas_quitar_canal_actas  # noqa: E402,F401

__all__ = ["actuacion"]
