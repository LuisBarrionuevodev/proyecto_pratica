from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.database import db
from app.models import CatalogContraproducencia, CatalogTipoActuacion

from app.domains.actuaciones.schemas.list_filters import _coerce_catalog_value


class CompletarTrabajoCierreIn(BaseModel):
    """
    Cierre operativo de una fila Completar trabajo (PR2).

    - `contraproducencia` vacía o ausente: visita **realizada** (`estado_ejecucion` REALIZADO).
    - `contraproducencia` con valor: visita **no realizada**; se normaliza y aplica reingreso o cierre.

    No incluye previas (acta notificación/comprobación previa): no son obligatorias en este flujo
    y no se muestran en Completar trabajo; el origen se modela vía iniciador.

    `tipo_actuacion` y `contraproducencia` (si vienen) se validan contra catálogo en DB.
    """

    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None
    rubro_nombre: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    observaciones_ejecucion: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("tipo_actuacion", mode="before")
    @classmethod
    def coerce_tipo_actuacion_catalog(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        s = v.strip()
        if not s:
            return None
        if db.session is None:  # pragma: no cover - defensivo
            return s
        return _coerce_catalog_value(
            s,
            CatalogTipoActuacion,
            "tipo_actuacion",
            strip_prefix="TIPO.",
        )

    @field_validator("contraproducencia", mode="before")
    @classmethod
    def coerce_contraproducencia_catalog(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return v
        s = v.strip()
        if not s:
            return None
        if db.session is None:  # pragma: no cover
            return s
        return _coerce_catalog_value(s, CatalogContraproducencia, "contraproducencia")

    @field_validator("rubro_nombre", "calle", "numero", mode="before")
    @classmethod
    def strip_optional_str(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v

    @field_validator("observaciones_ejecucion", mode="before")
    @classmethod
    def strip_obs(cls, v: object) -> object:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v
