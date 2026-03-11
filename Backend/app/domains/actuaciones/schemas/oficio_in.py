from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator


class OficioCreateIn(BaseModel):
    """
    Payload para cargar oficio desde una actuación.

    Valida campos editables del modal "Cargar oficio" y datos del expediente de respuesta.
    """

    numero_oficio: str
    fecha_oficio: date
    juzgado_id: int
    causa: str | None = None
    numero_expediente_oficio: str
    fecha_expediente_oficio: date
    # Compat temporal: se acepta pero se ignora; el backend deriva anio desde fecha_expediente_oficio.
    anio_expediente_oficio: int | None = None

    @field_validator("numero_oficio")
    @classmethod
    def validate_numero_oficio(cls, value: str) -> str:
        v = str(value or "").strip()
        if not v:
            raise ValueError("numero_oficio es obligatorio")
        return v

    @field_validator("juzgado_id")
    @classmethod
    def validate_juzgado_id(cls, value: int) -> int:
        if int(value) <= 0:
            raise ValueError("juzgado_id inválido")
        return int(value)

    @field_validator("numero_expediente_oficio")
    @classmethod
    def validate_numero_expediente(cls, value: str) -> str:
        v = str(value or "").strip()
        if not v:
            raise ValueError("numero_expediente_oficio es obligatorio")
        return v

    @field_validator("causa")
    @classmethod
    def validate_causa_numerica(cls, value: str | None) -> str | None:
        if value is None:
            return None
        v = str(value).strip()
        if not v:
            return None
        if not v.isdigit():
            raise ValueError("causa debe ser numérica")
        return v

