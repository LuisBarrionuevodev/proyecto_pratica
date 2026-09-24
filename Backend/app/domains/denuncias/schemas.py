from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class DenunciaCreateRequest(BaseModel):
    fecha: date
    domicilio_id: int | None = Field(default=None, ge=1)
    calle: str | None = Field(default=None, min_length=1, max_length=255)
    numero: str | None = Field(default=None, min_length=1, max_length=200)
    interseccion: str | None = Field(default=None, min_length=1, max_length=255)
    motivo: str = Field(..., min_length=1, max_length=2000)

    @field_validator("motivo")
    @classmethod
    def normalize_motivo(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("motivo es obligatorio.")
        return s

    @field_validator("calle", "numero", "interseccion")
    @classmethod
    def normalize_optional_str(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class DenunciaOut(BaseModel):
    id: int
    fecha: str
    anio: int
    mes: int
    domicilio_id: int
    motivo: str
    estado: str
    created_by_user_id: int
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
    iniciador_ruta_id: int


class DenunciasGestionFilters(BaseModel):
    desde: date | None = None
    hasta: date | None = None
    estado: str | None = "all"
    page: int = 1
    page_size: int = 50

    @field_validator("estado", mode="before")
    @classmethod
    def normalize_estado(cls, v: str | None) -> str:
        s = (v or "all").strip().lower()
        if s not in {"all", "hechas", "no_hechas"}:
            raise ValueError("estado inválido. Use all|hechas|no_hechas")
        return s

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page debe ser >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page_size debe ser >= 1")
        if v > 500:
            raise ValueError("page_size no puede superar 500")
        return v

    @model_validator(mode="after")
    def apply_defaults(self) -> "DenunciasGestionFilters":
        if self.desde is None and self.hasta is None:
            today = date.today()
            self.desde = date(today.year, today.month, 1)
            self.hasta = today
        elif self.desde is not None and self.hasta is None:
            self.hasta = date.today()
        elif self.desde is None and self.hasta is not None:
            self.desde = date(self.hasta.year, self.hasta.month, 1)

        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")
        return self


class DenunciaGestionRowIn(BaseModel):
    id: int = Field(..., ge=1)
    fecha: date
    calle: str = Field(..., min_length=1, max_length=255)
    numero: str = Field(..., min_length=1, max_length=200)
    numero_tipo: str | None = None
    motivo: str = Field(..., min_length=1, max_length=2000)
    estado: str = Field(..., min_length=1, max_length=50)

    @field_validator("calle", "numero", "motivo", "estado", mode="before")
    @classmethod
    def normalize_str(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v: str) -> str:
        up = v.upper()
        if up not in {"ABIERTA", "CERRADA", "DESCARTADA"}:
            raise ValueError("estado inválido.")
        return up

    @field_validator("numero_tipo", mode="before")
    @classmethod
    def normalize_numero_tipo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().upper()
        if s in {"NUMERO", "ESQUINA"}:
            return s
        return None
