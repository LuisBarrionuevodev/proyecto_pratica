from __future__ import annotations

from pydantic import BaseModel, Field


class NoRealizadasPorTipo(BaseModel):
    inspeccion: int = Field(ge=0)
    reinspeccion_oficio: int = Field(ge=0)
    reinspeccion_notificacion: int = Field(ge=0)
    denuncia: int = Field(ge=0)


class ContraproducenciaCantidadItem(BaseModel):
    contraproducencia: str
    cantidad: int = Field(ge=0)


class DistritoNoRealizadasItem(BaseModel):
    distrito_id: int
    distrito_codigo: str
    distrito_nombre: str
    cantidad: int = Field(ge=0)


class IndicadoresNoRealizadasOut(BaseModel):
    """Respuesta JSON de GET /api/indicadores/no-realizadas."""

    por_tipo: NoRealizadasPorTipo
    top_contraproducencias: list[ContraproducenciaCantidadItem]
    distritos_con_mas_no_realizadas: list[DistritoNoRealizadasItem]

    def to_json_response(self) -> dict:
        return self.model_dump(mode="json")
