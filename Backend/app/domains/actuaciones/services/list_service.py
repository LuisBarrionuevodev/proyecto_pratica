from __future__ import annotations

from typing import Dict, Any, List

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database import db
from app.models import Actuaciones, OrdenTrabajo
from app.domains.actuaciones.schemas.list_filters import ActuacionesListFilters
from app.utils.actas import acta_6


def listar_actuaciones_con_filtros(filters: ActuacionesListFilters) -> Dict[str, Any]:
    """
    Lista actuaciones aplicando filtros y paginación.
    
    Args:
        filters: Objeto con filtros validados y normalizados (desde, hasta, tipo, etc.)
    
    Returns:
        {
            "items": [...],  # lista de Actuaciones (modelo DB)
            "meta": {
                "total": 123,
                "page": 1,
                "page_size": 50,
                "desde": "2025-01-01",
                "hasta": "2025-01-31",
                "tipo": "INSPECCION",
                "contraproducencia": "LOCAL CERRADO",
                "orden_trabajo": None
            }
        }
    
    Raises:
        ValueError: si orden_trabajo no existe.
    """
    query = Actuaciones.query.options(joinedload(Actuaciones.inspector))

    # Filtro por rango de fechas (siempre están presentes tras validator)
    if filters.desde:
        query = query.filter(Actuaciones.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Actuaciones.fecha <= filters.hasta)
    
    # Filtro por tipo
    if filters.tipo:
        query = query.filter(func.upper(Actuaciones.tipo) == filters.tipo)
    
    # Filtro por contraproducencia
    if filters.contraproducencia:
        query = query.filter(func.upper(Actuaciones.contraproducencia) == filters.contraproducencia)
    
    # Filtro por orden de trabajo (búsqueda exacta, normalizado a 6 dígitos)
    if filters.orden_trabajo:
        # Normalizar OT a 6 dígitos (ej: "123" -> "000123")
        ot_normalizado = acta_6(filters.orden_trabajo)
        
        ot = (
            OrdenTrabajo.query
            .filter(OrdenTrabajo.numero == ot_normalizado)
            .first()
        )
        if not ot:
            raise ValueError(f"No existe la orden de trabajo '{filters.orden_trabajo}' (buscado como '{ot_normalizado}')")
        
        query = query.filter(Actuaciones.orden_trabajo_id == ot.id)
    
    # Contar total antes de paginar
    total = query.count()
    
    # Ordenar y paginar
    query = query.order_by(Actuaciones.id.desc())
    offset = (filters.page - 1) * filters.page_size
    items = query.offset(offset).limit(filters.page_size).all()
    
    return {
        "items": items,
        "meta": {
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "desde": filters.desde.isoformat() if filters.desde else None,
            "hasta": filters.hasta.isoformat() if filters.hasta else None,
            "tipo": filters.tipo,
            "contraproducencia": filters.contraproducencia,
            "orden_trabajo": filters.orden_trabajo,
        }
    }
