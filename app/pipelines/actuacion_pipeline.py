from typing import Any, Dict
from app.schemas.grid.actuacion_row import ActuacionGridRowIn
from app.mappers.grid.actuacion_row_mapper import map_actuacion_row

def row_dict_to_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    row = ActuacionGridRowIn(**data)
    return map_actuacion_row(row)