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
    calle = getattr(dom, "calle", None)
    numero = getattr(dom, "numero", None)
    calle_normalizada = getattr(dom, "calle_normalizada", None)
    calle_estado = getattr(dom, "calle_norm_status", None)
    calle_score = getattr(dom, "calle_norm_score", None)
    calle_catalogo_id = getattr(dom, "calle_catalogo_id", None)
    domicilio_id = getattr(dom, "id", None)

    calle_mostrar = calle_normalizada if calle_estado == "OK" and calle_normalizada else calle
    calle_sugerida = calle_normalizada if calle_normalizada else None

    return {
        "id": rel.id,
        "fecha": fecha_iso,
        "inspector": inspector_nombre,
        "calle": calle,
        "numero": numero,
        "domicilio_id": domicilio_id,
        "calle_normalizada": calle_normalizada,
        "calle_estado": calle_estado,
        "calle_score": calle_score,
        "calle_catalogo_id": calle_catalogo_id,
        "calle_sugerida": calle_sugerida,
        "calle_mostrar": calle_mostrar,
        "rubro": getattr(rub, "nombre", None),
        "contraproducencia": rel.contraproducencia,
    }
