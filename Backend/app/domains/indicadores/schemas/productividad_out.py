from __future__ import annotations

from pydantic import BaseModel, Field


class InspectorRealizadasItem(BaseModel):
    inspector_id: int
    inspector: str
    total_realizadas: int = Field(ge=0)
    inspecciones: int = Field(ge=0)
    reinspecciones_oficio: int = Field(ge=0)
    reinspecciones_notificacion: int = Field(ge=0)
    denuncias: int = Field(ge=0)
    otras: int = Field(ge=0, default=0)
    tipo_principal: str


class InspectorNoRealizadasItem(BaseModel):
    inspector_id: int
    inspector: str
    total_no_realizadas: int = Field(ge=0)
    contraproducencia_principal: str
    local_cerrado: int = Field(ge=0, default=0)
    no_existe: int = Field(ge=0, default=0)
    no_se_ratifico: int = Field(ge=0, default=0)
    clima: int = Field(ge=0, default=0)
    otras: int = Field(ge=0, default=0)
    inspecciones: int = Field(ge=0, default=0)
    reinspecciones_oficio: int = Field(ge=0, default=0)
    reinspecciones_notificacion: int = Field(ge=0, default=0)
    denuncias: int = Field(ge=0, default=0)


class InspectorActasItem(BaseModel):
    inspector_id: int
    inspector: str
    notificacion: int = Field(ge=0)
    comprobacion: int = Field(ge=0)
    clausura: int = Field(ge=0)
    decomiso: int = Field(ge=0)
    total_actas: int = Field(ge=0)


class IndicadoresProductividadOut(BaseModel):
    """
    Respuesta JSON de GET /api/indicadores/productividad.

    Agregaciones por inspector desde cierres de ruta y actas labradas del periodo.
    """

    inspectores_realizadas: list[InspectorRealizadasItem]
    inspectores_no_realizadas: list[InspectorNoRealizadasItem]
    actas_por_inspector: list[InspectorActasItem]

    def to_json_response(self) -> dict:
        return self.model_dump(mode="json")
