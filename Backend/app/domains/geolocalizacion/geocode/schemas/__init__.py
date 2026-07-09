"""Schemas Pydantic del dominio geocode."""

from .gestion_domicilios_query import GestionDomiciliosQuery
from .gestion_domicilios_response import (
    GestionDomiciliosMapPointOut,
    GestionDomiciliosPaginationOut,
    GestionDomiciliosResponse,
    GestionDomiciliosRowOut,
    GestionDomiciliosRowTecnicoOut,
    GestionDomiciliosSummaryOut,
)

__all__ = [
    "GestionDomiciliosQuery",
    "GestionDomiciliosMapPointOut",
    "GestionDomiciliosPaginationOut",
    "GestionDomiciliosResponse",
    "GestionDomiciliosRowOut",
    "GestionDomiciliosRowTecnicoOut",
    "GestionDomiciliosSummaryOut",
]
