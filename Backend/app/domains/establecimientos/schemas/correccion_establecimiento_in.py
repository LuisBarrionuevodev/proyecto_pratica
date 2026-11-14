"""Entrada del canal de corrección controlada (ficha de establecimiento)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_NUMERO_TIPOS = ("NUMERO", "ESQUINA", "OTRO")


def _strip_opt(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


class ContribuyenteCorreccionIn(BaseModel):
    """
    Corrección de datos del mismo contribuyente (no cambio de titular).

    Campos omitidos se conservan. No admite ``contribuyente_id`` ni ``limpiar_contribuyente``.
    """

    model_config = ConfigDict(extra="forbid")

    documento: Optional[str] = Field(None, max_length=11)
    apellido: Optional[str] = Field(None, max_length=128)
    nombre: Optional[str] = Field(None, max_length=128)
    razon_social: Optional[str] = Field(None, max_length=255)

    @field_validator("documento", "apellido", "nombre", "razon_social", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class DomicilioCorreccionIn(BaseModel):
    """Corrección de calle/número/esquina del domicilio de origen de la ficha."""

    model_config = ConfigDict(extra="forbid")

    calle: Optional[str] = Field(None, max_length=128)
    numero: Optional[str] = Field(None, max_length=200)
    numero_tipo: Optional[Literal["NUMERO", "ESQUINA", "OTRO"]] = None
    esquina: Optional[str] = Field(None, max_length=255)

    @field_validator("calle", "numero", "esquina", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> Optional[str]:
        return _strip_opt(str(v) if v is not None else None)

    @field_validator("numero_tipo", mode="before")
    @classmethod
    def norm_numero_tipo(cls, v: object) -> Optional[str]:
        if v is None or str(v).strip() == "":
            return None
        s = str(v).strip().upper()
        if s not in _NUMERO_TIPOS:
            raise ValueError("numero_tipo debe ser NUMERO, ESQUINA u OTRO.")
        return s


class CorreccionEstablecimientoIn(BaseModel):
    """
    Payload de preview/aplicación.

    Parámetros:
        contribuyente: bloque opcional de corrección de titular (mismos datos, mismo id).
        domicilio: bloque opcional de corrección de dirección de la ficha.
        confirmado: obligatorio en True para persistir.

    Errores:
        extra=forbid rechaza cambio de titular (contribuyente_id / limpiar_contribuyente).
    """

    model_config = ConfigDict(extra="forbid")

    contribuyente: Optional[ContribuyenteCorreccionIn] = None
    domicilio: Optional[DomicilioCorreccionIn] = None
    confirmado: bool = False

    @model_validator(mode="after")
    def requiere_bloque(self) -> "CorreccionEstablecimientoIn":
        if self.contribuyente is None and self.domicilio is None:
            raise ValueError("Debe indicar contribuyente y/o domicilio a corregir.")
        return self
