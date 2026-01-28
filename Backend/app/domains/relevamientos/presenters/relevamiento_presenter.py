from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Relevamiento


def relevamiento_to_row(rel: Relevamiento) -> Dict[str, Any]:
    """
    Convierte un Relevamiento a formato plano consumible por la UI.

    Retorna:
    - id
    - fecha (YYYY-MM-DD)
    - inspector (nombre)
    - calle
    - numero
    - rubro (nombre)
    - contraproducencia
    """
    fecha_iso: Optional[str] = rel.fecha.isoformat() if rel.fecha else None
    inspector_nombre = rel.inspector.nombre if rel.inspector else None
    dom = rel.domicilio
    rub = rel.rubro

    return {
        "id": rel.id,
        "fecha": fecha_iso,
        "inspector": inspector_nombre,
        "calle": getattr(dom, "calle", None),
        "numero": getattr(dom, "numero", None),
        "rubro": getattr(rub, "nombre", None),
        "contraproducencia": rel.contraproducencia,
    }
