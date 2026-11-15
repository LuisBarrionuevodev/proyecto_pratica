"""Entrada del canal de vinculación de ficha a contribuyente existente."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VinculacionEstablecimientoIn(BaseModel):
    """
    Payload de preview/aplicación de vinculación.

    Parámetros:
        documento: CUIT/DNI del contribuyente destino (lookup normalizado en el service).
        fingerprint: token de alcance emitido por el preview (obligatorio al confirmar).
        confirmado: True solo para persistir.

    Errores:
        extra=forbid rechaza contribuyente_id, limpiar_contribuyente y campos ajenos.
        documento vacío o > 11 caracteres.
    """

    model_config = ConfigDict(extra="forbid")

    documento: str = Field(..., max_length=11)
    fingerprint: str | None = Field(None, max_length=128)
    confirmado: bool = False

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

    @model_validator(mode="after")
    def no_titular_en_body(self) -> "VinculacionEstablecimientoIn":
        # Defensa extra: extra=forbid ya bloquea contribuyente_id / limpiar_contribuyente.
        return self
