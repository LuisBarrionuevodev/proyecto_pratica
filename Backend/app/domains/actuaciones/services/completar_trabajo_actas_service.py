from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones

from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.notificacion import attach_notificacion


def aplicar_notificacion_y_comprobacion_completar_trabajo(
    act: Actuaciones,
    *,
    notificacion: Optional[Dict[str, Any]],
    comprobacion: Optional[Dict[str, Any]],
) -> None:
    """
    Crea o actualiza Notificación y Comprobación del día y las vincula a la actuación.

    Qué hace:
    - Delega en `attach_notificacion` / `attach_comprobacion` (upsert por acta+año, motivos catálogo).
    - Hace `flush` tras cada attach para que `act.notificacion_id` / `act.comprobacion_id` estén
      resueltos antes de oficio/expediente en el mismo `aplicar_payload_actuacion`.

    Parámetros:
        act: actuación destino (con `anio`, `mes`, `fecha` coherentes).
        notificacion: dict canónico (`acta_num`, `motivos`) o None.
        comprobacion: dict canónico (`acta_num`, `motivo`) o None.

    Errores:
        ValueError: reglas de attach (motivo comprobación vacío, acta duplicada, motivo inválido, etc.).

    Side effects:
        Modifica `act` y sesión SQLAlchemy; no hace commit.
    """
    if notificacion is not None:
        attach_notificacion(act, notificacion)
        db.session.flush()
    if comprobacion is not None:
        attach_comprobacion(act, comprobacion)
        db.session.flush()
