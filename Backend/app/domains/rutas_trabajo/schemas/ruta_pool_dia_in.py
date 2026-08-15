from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


_POOL_ESTADOS = {"EN_POOL", "ASIGNADO_A_RUTA", "DESCARTADO"}
_ORIGEN_TIPOS = {
    "INICIADOR",
    "ACTUACION_NOTIF",
    "ACTUACION_COMP",
    "RELEVAMIENTO",
    "DENUNCIA",
    "MANUAL",
}


class RutaPoolDiaListQuery(BaseModel):
    """
    Filtros de listado del pool del día.

    Parámetros:
        fecha: día operativo obligatorio.
        turno_id, distrito_id, rubro_id, estado, q: filtros opcionales.
        page, per_page: paginación 1-based.
    """

    fecha: date
    turno_id: Optional[int] = None
    distrito_id: Optional[int] = None
    rubro_id: Optional[int] = None
    estado: Optional[str] = None
    q: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)

    @field_validator("estado")
    @classmethod
    def _validate_estado(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        val = str(v).strip().upper()
        if val not in _POOL_ESTADOS:
            raise ValueError("estado inválido")
        return val

    @field_validator("q")
    @classmethod
    def _strip_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class RutaPoolDiaCreateIn(BaseModel):
    """
    Alta en pool del día.

    Fase 1: requiere ``iniciador_ruta_id`` (alias ``iniciador_id``).
    """

    origen_tipo: Optional[str] = None
    iniciador_ruta_id: Optional[int] = Field(default=None, ge=1)
    iniciador_id: Optional[int] = Field(default=None, ge=1)
    actuacion_id: Optional[int] = Field(default=None, ge=1)
    fecha: date
    turno_id: Optional[int] = Field(default=None, ge=1)
    ruta_trabajo_id: Optional[int] = Field(default=None, ge=1)
    observacion: Optional[str] = None

    @field_validator("origen_tipo")
    @classmethod
    def _validate_origen(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        val = str(v).strip().upper()
        if val not in _ORIGEN_TIPOS:
            raise ValueError("origen_tipo inválido")
        return val

    @model_validator(mode="after")
    def _resolver_iniciador_id(self) -> "RutaPoolDiaCreateIn":
        resolved = self.iniciador_ruta_id or self.iniciador_id
        if resolved is None and self.actuacion_id is None:
            raise ValueError("Debe indicar iniciador_ruta_id o iniciador_id")
        if resolved is not None:
            self.iniciador_ruta_id = int(resolved)
        return self


class RutaPoolAgregarDesdePoolIn(BaseModel):
    """
    Asignación bulk desde pool hacia ruta BORRADOR.

    Parámetros:
        pool_ids: ids de filas EN_POOL.
        grupo_id: grupo destino obligatorio en fase inicial.
    """

    pool_ids: list[int] = Field(min_length=1)
    grupo_id: int = Field(ge=1)

    @field_validator("pool_ids")
    @classmethod
    def _dedupe_pool_ids(cls, v: list[int]) -> list[int]:
        seen: set[int] = set()
        out: list[int] = []
        for raw in v:
            pid = int(raw)
            if pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
        if not out:
            raise ValueError("pool_ids no puede estar vacío")
        return out
