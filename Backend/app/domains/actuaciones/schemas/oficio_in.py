from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator, model_validator


class OficioCreateIn(BaseModel):
    """
    Payload para cargar oficio desde una actuación.

    Valida campos editables del modal "Cargar oficio" y datos del expediente de respuesta.

    **Fechas:** en negocio, la fecha del oficio y la del expediente de respuesta son la misma.
    Si no se envía ``fecha_expediente_oficio`` o difiere de ``fecha_oficio``, se unifica a
    ``fecha_oficio`` (compatibilidad con clientes que aún envían dos campos).
    """

    numero_oficio: str
    fecha_oficio: date
    juzgado_id: int
    causa: str | None = None
    numero_expediente_oficio: str
    fecha_expediente_oficio: date | None = None
    # Compat temporal: se acepta pero se ignora; el backend deriva anio desde la fecha unificada.
    anio_expediente_oficio: int | None = None

    @model_validator(mode="after")
    def _unificar_fecha_oficio_y_expediente_respuesta(self) -> "OficioCreateIn":
        fo = self.fecha_oficio
        if self.fecha_expediente_oficio is None or self.fecha_expediente_oficio != fo:
            self.fecha_expediente_oficio = fo
        return self

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

