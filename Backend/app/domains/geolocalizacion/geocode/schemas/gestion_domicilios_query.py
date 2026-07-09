from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

StatusOperativoFilter = Literal[
    "requiere_accion",
    "sin_punto",
    "punto_dudoso",
    "error",
    "manual",
    "geolocalizado",
    "todos",
]

StatusOperativoRow = Literal[
    "sin_punto",
    "punto_dudoso",
    "error",
    "manual",
    "geolocalizado",
]

MapMode = Literal["problematic", "visible", "all", "manual", "errors"]

SortMode = Literal["requiere_accion_desc", "updated_desc", "domicilio_asc"]


class GestionDomiciliosQuery(BaseModel):
    """
    Query params de GET /map/gestion-domicilios (PR6C.2 contrato).

    Validación de entrada; la implementación real llegará en PR6C.3+.
    """

    q: Optional[str] = Field(default=None, description="Búsqueda libre calle/número.")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    status_operativo: StatusOperativoFilter = Field(default="requiere_accion")
    include_map_points: bool = Field(default=True)
    map_mode: MapMode = Field(default="problematic")
    bbox: Optional[str] = Field(
        default=None,
        description="Viewport: min_lat,min_lng,max_lat,max_lng",
    )
    sort: SortMode = Field(default="requiere_accion_desc")
    include_tecnico: bool = Field(default=False)

    @classmethod
    def from_request_args(cls, args: dict[str, str]) -> "GestionDomiciliosQuery":
        """
        Parsea query string Flask a modelo validado.

        Parámetros:
            args: ``request.args.to_dict()``.

        Retorno:
            Instancia validada.

        Errores:
            pydantic.ValidationError: parámetros inválidos.
        """
        include_map_points = args.get("include_map_points", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        include_tecnico = args.get("include_tecnico", "0").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        page_raw = args.get("page", "1")
        page_size_raw = args.get("page_size", "50")
        return cls(
            q=args.get("q") or None,
            page=int(page_raw),
            page_size=int(page_size_raw),
            status_operativo=args.get("status_operativo") or "requiere_accion",  # type: ignore[arg-type]
            include_map_points=include_map_points,
            map_mode=args.get("map_mode") or "problematic",  # type: ignore[arg-type]
            bbox=args.get("bbox") or None,
            sort=args.get("sort") or "requiere_accion_desc",  # type: ignore[arg-type]
            include_tecnico=include_tecnico,
        )
