from __future__ import annotations

from typing import Dict, Any, List

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Contribuyente,
    Decomiso,
    Domicilio,
    Expediente,
    Inspeccion,
    Notificacion,
    Oficio,
    OrdenTrabajo,
    Rubro,
)
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
    query = Actuaciones.query.options(
        joinedload(Actuaciones.inspector),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(Actuaciones.epicollect_detalle),
        joinedload(Actuaciones.notificacion).joinedload(Notificacion.motivos),
        joinedload(Actuaciones.comprobacion),
    )

    busqueda_global = bool(filters.q or filters.orden_trabajo or filters.actuacion_id)

    if filters.desde:
        query = query.filter(Actuaciones.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Actuaciones.fecha <= filters.hasta)

    if filters.actuacion_id:
        query = query.filter(Actuaciones.id == int(filters.actuacion_id))

    if filters.q:
        term = filters.q.strip()
        like = f"%{term}%"
        ot_norm = acta_6(term) if term.replace(" ", "").isdigit() else None
        acta_norm = acta_6(term) if term.replace(" ", "").isdigit() else None
        query = (
            query.outerjoin(OrdenTrabajo, Actuaciones.orden_trabajo_id == OrdenTrabajo.id)
            .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
            .outerjoin(Contribuyente, Domicilio.contribuyente_id == Contribuyente.id)
            .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
            .outerjoin(Inspeccion, Inspeccion.actuacion_id == Actuaciones.id)
            .outerjoin(Notificacion, Actuaciones.notificacion_id == Notificacion.id)
            .outerjoin(Comprobacion, Actuaciones.comprobacion_id == Comprobacion.id)
            .outerjoin(Clausura, Clausura.actuacion_id == Actuaciones.id)
            .outerjoin(Decomiso, Decomiso.actuacion_id == Actuaciones.id)
            .outerjoin(
                Expediente,
                and_(
                    or_(
                        Expediente.comprobacion_id == Actuaciones.comprobacion_id,
                        Expediente.notificacion_id == Actuaciones.notificacion_id,
                    ),
                    Expediente.deleted_at.is_(None),
                ),
            )
            .outerjoin(
                Oficio,
                and_(
                    Oficio.comprobacion_id == Actuaciones.comprobacion_id,
                    Oficio.deleted_at.is_(None),
                ),
            )
        )
        conds = [
            OrdenTrabajo.numero_acta.ilike(like),
            Domicilio.calle.ilike(like),
            Domicilio.numero.ilike(like),
            Contribuyente.apellido.ilike(like),
            Contribuyente.nombre.ilike(like),
            Contribuyente.documento.ilike(like),
            Rubro.nombre.ilike(like),
            Actuaciones.nombre_local.ilike(like),
            Expediente.numero_expediente.ilike(like),
            Oficio.numero_oficio.ilike(like),
        ]
        if ot_norm:
            conds.append(OrdenTrabajo.numero_acta == ot_norm)
        if acta_norm:
            conds.extend(
                [
                    Inspeccion.numero_acta == acta_norm,
                    Notificacion.numero_acta == acta_norm,
                    Comprobacion.numero_acta == acta_norm,
                    Clausura.numero_acta == acta_norm,
                    Decomiso.numero_acta == acta_norm,
                    Expediente.numero_expediente == acta_norm,
                ]
            )
        query = query.filter(or_(*conds))
    
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
            OrdenTrabajo.query.filter(
                OrdenTrabajo.numero_acta == ot_normalizado,
                OrdenTrabajo.deleted_at.is_(None),
            )
            .order_by(OrdenTrabajo.id.desc())
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
            "actuacion_id": filters.actuacion_id,
            "q": filters.q,
            "busqueda_global": busqueda_global,
        }
    }
