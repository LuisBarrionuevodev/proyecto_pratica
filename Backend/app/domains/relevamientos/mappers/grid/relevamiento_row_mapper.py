from __future__ import annotations

from typing import Any, Dict, Optional

from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def map_relevamiento_row(row: RelevamientoGridRowIn) -> Dict[str, Any]:
    """
    Mapper UI -> Payload limpio para services (sin DB).
    - fecha ya es date
    """
    payload: Dict[str, Any] = {
        "id": row.id,
        "fecha": row.fecha.isoformat(),
        "inspector_nombre": _clean_str(row.inspector),
        "domicilio": {
            "calle": _clean_str(row.calle),
            "numero": _clean_str(row.numero),
            "numero_tipo": _clean_str(row.numero_tipo),
        },
        "rubro_nombre": _clean_str(row.rubro),
        "nombre_fantasia": row.nombre_fantasia,
        "angulo_esquina": row.angulo_esquina,
        "turno_carga": row.turno,
        "esta_abierto": row.esta_abierto,
    }
    return payload
