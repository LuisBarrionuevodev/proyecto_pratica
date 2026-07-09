"""Schemas Pydantic del dominio geocode."""

from .gestion_domicilios_query import GestionDomiciliosQuery
from .gestion_domicilios_response import (
    GestionDomiciliosMapPointOut,
    GestionDomiciliosMapPointsMetaOut,
    GestionDomiciliosPaginationOut,
    GestionDomiciliosResponse,
    GestionDomiciliosRowOut,
    GestionDomiciliosRowTecnicoOut,
    GestionDomiciliosSummaryOut,
)

__all__ = [
    "GestionDomiciliosQuery",
    "GestionDomiciliosMapPointOut",
    "GestionDomiciliosMapPointsMetaOut",
    "GestionDomiciliosPaginationOut",
    "GestionDomiciliosResponse",
    "GestionDomiciliosRowOut",
    "GestionDomiciliosRowTecnicoOut",
    "GestionDomiciliosSummaryOut",
]
