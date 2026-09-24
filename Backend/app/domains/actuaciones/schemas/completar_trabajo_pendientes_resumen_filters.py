from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator, model_validator

# Límite de ventana para evitar consultas pesadas; suficiente para chips / calendario operativo.
COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS = 120


class CompletarTrabajoPendientesResumenQuery(BaseModel):
    """
    Query params para resumen de pendientes Completar trabajo agrupados por día de ruta publicada.

    Parámetros:
        fecha_desde: inicio inclusive del rango (`RutaTrabajo.fecha`).
        fecha_hasta: fin inclusive del rango.

    Validación:
        fecha_desde <= fecha_hasta; rango máximo `COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS` días.
    """

    fecha_desde: date
    fecha_hasta: date

    @field_validator("fecha_desde", "fecha_hasta", mode="before")
    @classmethod
    def parse_fecha(cls, v: object) -> object:
        if isinstance(v, str) and v.strip():
            return date.fromisoformat(v.strip())
        return v

    @model_validator(mode="after")
    def validar_orden_y_amplitud(self) -> CompletarTrabajoPendientesResumenQuery:
        if self.fecha_desde > self.fecha_hasta:
            raise ValueError("fecha_desde no puede ser posterior a fecha_hasta")
        span = (self.fecha_hasta - self.fecha_desde).days
        if span > COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS:
            raise ValueError(
                f"El rango no puede superar {COMPLETAR_TRABAJO_PENDIENTES_RESUMEN_MAX_DIAS} días "
                f"(solicitados: {span + 1} días)"
            )
        return self
