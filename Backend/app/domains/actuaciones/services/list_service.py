from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.domains.actuaciones.schemas.list_filters import (
    ActuacionesListFilters,
    _has_anchor_filters,
)
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
from app.models.actuaciones_inspector import actuaciones_inspector
from app.utils.actas import acta_6


def _contains_ci(column, term: str):
    """Subcadena case-insensitive."""
    t = term.strip().lower()
    return func.lower(column).contains(t)


def _documento_prefix(column, term: str):
    """Prefijo exacto/prefijo sobre documento (sin comodín inicial)."""
    t = term.strip().replace(" ", "").replace("-", "").lower()
    return func.lower(column).like(f"{t}%")


def _apply_filtros_especificos(query, filters: ActuacionesListFilters):
    """
    Filtros PERF.1-A2: condiciones independientes con EXISTS (sin joins globales).

    Parámetros:
        query: consulta base sobre Actuaciones.
        filters: filtros validados.

    Retorno:
        Query con restricciones AND adicionales.
    """
    if filters.calle_q:
        term = filters.calle_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    _contains_ci(Domicilio.calle, term),
                )
            )
        )

    if filters.documento_q:
        term = filters.documento_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    Contribuyente.id == Domicilio.contribuyente_id,
                    Contribuyente.deleted_at.is_(None),
                    _documento_prefix(Contribuyente.documento, term),
                )
            )
        )

    if filters.contribuyente_q:
        term = filters.contribuyente_q.strip()
        query = query.filter(
            exists().where(
                and_(
                    Domicilio.id == Actuaciones.domicilio_id,
                    Domicilio.deleted_at.is_(None),
                    Contribuyente.id == Domicilio.contribuyente_id,
                    Contribuyente.deleted_at.is_(None),
                    or_(
                        _contains_ci(Contribuyente.apellido, term),
                        _contains_ci(Contribuyente.nombre, term),
                        _contains_ci(Contribuyente.razon_social, term),
                    ),
                )
            )
        )

    if filters.inspector_id:
        iid = int(filters.inspector_id)
        query = query.filter(
            exists().where(
                and_(
                    actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
                    actuaciones_inspector.c.inspector_id == iid,
                    actuaciones_inspector.c.deleted_at.is_(None),
                )
            )
        )

    if filters.acta_inspeccion:
        num = filters.acta_inspeccion
        query = query.filter(
            exists().where(
                and_(
                    Inspeccion.actuacion_id == Actuaciones.id,
                    Inspeccion.numero_acta == num,
                )
            )
        )

    if filters.acta_notificacion:
        num = filters.acta_notificacion
        query = query.filter(
            exists().where(
                and_(
                    Notificacion.id == Actuaciones.notificacion_id,
                    Notificacion.numero_acta == num,
                )
            )
        )

    if filters.acta_comprobacion:
        num = filters.acta_comprobacion
        query = query.filter(
            exists().where(
                and_(
                    Comprobacion.id == Actuaciones.comprobacion_id,
                    Comprobacion.numero_acta == num,
                )
            )
        )

    if filters.acta_clausura:
        num = filters.acta_clausura
        query = query.filter(
            exists().where(
                and_(
                    Clausura.actuacion_id == Actuaciones.id,
                    Clausura.numero_acta == num,
                )
            )
        )

    if filters.acta_decomiso:
        num = filters.acta_decomiso
        query = query.filter(
            exists().where(
                and_(
                    Decomiso.actuacion_id == Actuaciones.id,
                    Decomiso.numero_acta == num,
                )
            )
        )

    return query


def _apply_q_legacy(query, term: str):
    """legacy compatibility — búsqueda global OR con joins (STAB-6)."""
    like = f"%{term.strip()}%"
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
    return query.filter(or_(*conds))


def listar_actuaciones_con_filtros(filters: ActuacionesListFilters) -> Dict[str, Any]:
    """
    Lista actuaciones aplicando filtros y paginación.

    Args:
        filters: Objeto con filtros validados y normalizados (desde, hasta, tipo, etc.)

    Returns:
        Dict con items (modelos Actuaciones) y meta de paginación.

    Raises:
        ValueError: si orden_trabajo no existe.
    """
    query = Actuaciones.query.options(
        joinedload(Actuaciones.inspector),
        joinedload(Actuaciones.inspeccion),
        joinedload(Actuaciones.clausura),
        joinedload(Actuaciones.decomiso),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(Actuaciones.epicollect_detalle),
        joinedload(Actuaciones.notificacion).joinedload(Notificacion.motivos),
        joinedload(Actuaciones.comprobacion),
    )

    busqueda_global = _has_anchor_filters(
        q=filters.q,
        orden_trabajo=filters.orden_trabajo,
        actuacion_id=filters.actuacion_id,
        calle_q=filters.calle_q,
        documento_q=filters.documento_q,
        contribuyente_q=filters.contribuyente_q,
        inspector_id=filters.inspector_id,
        acta_inspeccion=filters.acta_inspeccion,
        acta_notificacion=filters.acta_notificacion,
        acta_comprobacion=filters.acta_comprobacion,
        acta_clausura=filters.acta_clausura,
        acta_decomiso=filters.acta_decomiso,
    )

    if filters.desde:
        query = query.filter(Actuaciones.fecha >= filters.desde)
    if filters.hasta:
        query = query.filter(Actuaciones.fecha <= filters.hasta)

    if filters.actuacion_id:
        query = query.filter(Actuaciones.id == int(filters.actuacion_id))

    if filters.q:
        query = _apply_q_legacy(query, filters.q)

    query = _apply_filtros_especificos(query, filters)

    if filters.tipo:
        query = query.filter(func.upper(Actuaciones.tipo) == filters.tipo)

    if filters.contraproducencia:
        query = query.filter(func.upper(Actuaciones.contraproducencia) == filters.contraproducencia)

    if filters.orden_trabajo:
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
            raise ValueError(
                f"No existe la orden de trabajo '{filters.orden_trabajo}' "
                f"(buscado como '{ot_normalizado}')"
            )
        query = query.filter(Actuaciones.orden_trabajo_id == ot.id)

    total = query.count()

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
            "calle_q": filters.calle_q,
            "documento_q": filters.documento_q,
            "contribuyente_q": filters.contribuyente_q,
            "inspector_id": filters.inspector_id,
            "acta_inspeccion": filters.acta_inspeccion,
            "acta_notificacion": filters.acta_notificacion,
            "acta_comprobacion": filters.acta_comprobacion,
            "acta_clausura": filters.acta_clausura,
            "acta_decomiso": filters.acta_decomiso,
            "busqueda_global": busqueda_global,
        },
    }
