"""Entrada del canal de vinculación de ficha (existente o alta atómica)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip_opt(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


class VinculacionAltaIn(BaseModel):
    """
    Datos de identidad para crear el contribuyente destino (solo si no existe).

    Parámetros:
        apellido, nombre: persona física (ambos si no hay razón social).
        razon_social: alternativa a persona.

    Errores:
        extra=forbid. Falta nombre+apellido y razón social.
    """

    model_config = ConfigDict(extra="forbid")

    apellido: str | None = Field(None, max_length=128)
    nombre: str | None = Field(None, max_length=128)
    razon_social: str | None = Field(None, max_length=255)

    @field_validator("apellido", "nombre", "razon_social", mode="before")
    @classmethod
    def strip_opt(cls, v: object) -> str | None:
        return _strip_opt(v)

    @model_validator(mode="after")
    def identidad_minima(self) -> "VinculacionAltaIn":
        persona = bool(self.apellido and self.nombre)
        razon = bool(self.razon_social)
        if not persona and not razon:
            raise ValueError("Indicá nombre y apellido, o razón social.")
        return self


class VinculacionEstablecimientoIn(BaseModel):
    """
    Payload de preview/aplicación de vinculación.

    Parámetros:
        documento: CUIT/DNI del contribuyente destino (lookup normalizado en el service).
        fingerprint: token de alcance emitido por el preview (obligatorio al confirmar).
        confirmado: True solo para persistir.
        alta: identidad a crear si el documento no existe (None en búsqueda / existente).

    Errores:
        extra=forbid rechaza contribuyente_id, limpiar_contribuyente y campos ajenos.
        documento vacío o > 11 caracteres.
    """

    model_config = ConfigDict(extra="forbid")

    documento: str = Field(..., max_length=11)
    fingerprint: str | None = Field(None, max_length=128)
    confirmado: bool = False
    alta: VinculacionAltaIn | None = None

    @field_validator("documento", mode="before")
    @classmethod
    def strip_documento(cls, v: object) -> str:
        s = "" if v is None else str(v).strip()
        if not s:
            raise ValueError("El documento del contribuyente destino es obligatorio.")
        return s

    @field_validator("fingerprint", mode="before")
    @classmethod
    def strip_fingerprint(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None
