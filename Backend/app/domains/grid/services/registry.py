from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel

from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn
from app.domains.actuaciones.mappers.grid.actuacion_row_mapper import map_actuacion_row
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.grid.services.column_map_actuaciones import COLUMN_MAP_ACTUACIONES
from app.domains.grid.services.dup_key import build_dup_key

from app.domains.relevamientos.schemas.grid.relevamiento_row_in import RelevamientoGridRowIn
from app.domains.relevamientos.mappers.grid.relevamiento_row_mapper import map_relevamiento_row
from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload
from app.domains.relevamientos.services.update_service import actualizar_relevamiento
from app.domains.relevamientos.presenters.relevamiento_presenter import relevamiento_to_row
from app.domains.grid.services.column_map_relevamientos import COLUMN_MAP_RELEVAMIENTOS


@dataclass(frozen=True)
class GridDomainHandler:
    kind: str
    schema: Type[BaseModel]
    mapper: Callable[[Any], Dict[str, Any]]
    create_fn: Callable[[Dict[str, Any]], Any]
    update_fn: Callable[[int, Dict[str, Any]], Any]
    presenter: Callable[[Any], Dict[str, Any]]
    column_map: Dict[str, str]
    dup_key_builder: Optional[Callable[[Any], Optional[tuple[str, str]]]] = None


_REGISTRY: Dict[str, GridDomainHandler] = {
    "actuaciones": GridDomainHandler(
        kind="actuaciones",
        schema=ActuacionGridRowIn,
        mapper=map_actuacion_row,
        create_fn=crear_actuacion_desde_payload,
        update_fn=actualizar_actuacion,
        presenter=actuacion_to_grid_row,
        column_map=COLUMN_MAP_ACTUACIONES,
        dup_key_builder=build_dup_key,
    ),
    "relevamientos": GridDomainHandler(
        kind="relevamientos",
        schema=RelevamientoGridRowIn,
        mapper=map_relevamiento_row,
        create_fn=crear_relevamiento_desde_payload,
        update_fn=actualizar_relevamiento,
        presenter=relevamiento_to_row,
        column_map=COLUMN_MAP_RELEVAMIENTOS,
        dup_key_builder=None,
    ),
}


def get_handler(kind: str) -> GridDomainHandler:
    """
    Resuelve el handler de grid según `kind`.
    """
    key = (kind or "").strip().lower()
    if key not in _REGISTRY:
        raise ValueError(f"Grid kind inválido: {kind}")
    return _REGISTRY[key]
