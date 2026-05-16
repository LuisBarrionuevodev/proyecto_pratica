"""
Bandejas operativas unificadas para actas de comprobación (oficio / reinspección / recorrido).
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.domains.actuaciones.services.pendientes_service import _apply_distrito_optional, _apply_fecha
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import estado_recorrido_label
from app.models import Actuaciones, Domicilio, Expediente, IniciadorRuta, Oficio, RutaItem, RutaTrabajo
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters

# Rutas donde el trabajo sigue planificable / operativo; CERRADA y CANCELADA no retienen fuera de bandeja.
_ESTADOS_RUTA_ACTIVA_REINSP_OFICIO = ("BORRADOR", "PUBLICADA", "EN_CURSO")


def list_pendientes_reinspeccion_oficio(
    filters: ActuacionesPendientesFilters,
) -> List[Actuaciones]:
    """
    Actuaciones cuya comprobación tiene circuito documental listo y la reinspección por oficio
    **aún no está incorporada a una ruta operativa**.

    Criterio documental (igual que antes):

    - Expediente de envío de acta activo (``oficio_id`` NULL, no borrado).
    - Oficio administrativo activo (no borrado).
    - Expediente de respuesta al oficio activo (``oficio_id`` enlazado a oficio de la misma comprobación;
      ``tipo_expediente`` ``RESPUESTA_OFICIO`` o ``NULL`` en filas legadas sin enum).

    Exclusión (fuera de bandeja): existe ``RutaItem`` no soft-deleted cuyo ``IniciadorRuta`` es
    ``REINSPECCION_OFICIO`` no borrado para la misma actuación, y la ``RutaTrabajo`` vinculada está en
    ``BORRADOR``, ``PUBLICADA`` o ``EN_CURSO``. Si el iniciador está solo en memoria/backlog, si la ruta
    está ``CERRADA``/``CANCELADA``, o el ítem está soft-deleted, la fila **sigue** en bandeja.

    Rango de fechas y distrito: mismos helpers que el resto de bandejas (``Actuaciones.fecha``).
    """
    has_envio = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.is_(None),
            Expediente.deleted_at.is_(None),
        )
    )
    has_oficio = exists().where(
        and_(
            Oficio.comprobacion_id == Actuaciones.comprobacion_id,
            Oficio.deleted_at.is_(None),
        )
    )
    has_respuesta = exists().where(
        and_(
            Expediente.comprobacion_id == Actuaciones.comprobacion_id,
            Expediente.oficio_id.isnot(None),
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.deleted_at.is_(None),
            exists().where(
                and_(
                    Oficio.id == Expediente.oficio_id,
                    Oficio.comprobacion_id == Actuaciones.comprobacion_id,
                    Oficio.deleted_at.is_(None),
                )
            ),
        )
    )
    en_ruta_activa = exists(
        select(1)
        .select_from(RutaItem)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .where(
            and_(
                IniciadorRuta.actuacion_id == Actuaciones.id,
                IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
                IniciadorRuta.deleted_at.is_(None),
                RutaItem.deleted_at.is_(None),
                RutaTrabajo.estado_ruta.in_(_ESTADOS_RUTA_ACTIVA_REINSP_OFICIO),
            )
        )
    )
    q = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(has_envio, has_oficio, has_respuesta, ~en_ruta_activa)
        .options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            selectinload(Actuaciones.inspector),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.comprobacion),
        )
    )
    q = _apply_fecha(q, filters.desde, filters.hasta)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    return q.order_by(Actuaciones.id.desc()).all()


def list_comprobacion_recorrido(
    filters: ActuacionesPendientesFilters,
    *,
    contrib_q: Optional[str] = None,
    calle_q: Optional[str] = None,
    numero_q: Optional[str] = None,
    acta_comprobacion: Optional[str] = None,
    expediente_numero: Optional[str] = None,
    oficio_numero: Optional[str] = None,
    estado_recorrido: Optional[str] = None,
    tipo_final: Optional[str] = None,
    limit: int = 500,
) -> List[Actuaciones]:
    """
    Actuaciones con comprobación para vista consultiva de recorrido.
    Filtros de texto opcionales (subcadena, case-insensitive) aplicados en memoria sobre el grid row.
    ``contrib_q`` coincide con apellido, nombre y razón social del row.
    ``tipo_final`` filtra por ``resultado_cumplimiento_oficio`` (CUMPLE / NO_CUMPLE).
    """
    q = Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
    q = _apply_fecha(q, filters.desde, filters.hasta)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    rows: List[Actuaciones] = q.order_by(Actuaciones.id.desc()).limit(limit).all()

    from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

    counts_by_eo = build_counts_by_eo_from_actuaciones(rows)

    def _keep(act: Actuaciones) -> bool:
        row = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
        if contrib_q and contrib_q.strip():
            blob = (
                f"{row.get('contrib_apellido') or ''} {row.get('contrib_nombre') or ''} "
                f"{row.get('razon_social') or ''}"
            ).lower()
            if contrib_q.strip().lower() not in blob:
                return False
        if calle_q and calle_q.strip():
            if calle_q.strip().lower() not in (row.get("calle") or "").lower():
                return False
        if numero_q and numero_q.strip():
            if numero_q.strip().lower() not in (row.get("numero") or "").lower():
                return False
        if acta_comprobacion and acta_comprobacion.strip():
            ac = (row.get("acta_comprobacion_num") or "").lower()
            if acta_comprobacion.strip().lower() not in ac:
                return False
        if expediente_numero and expediente_numero.strip():
            ex = f"{row.get('expediente_numero') or ''}{row.get('expediente_anio') or ''}".lower()
            if expediente_numero.strip().lower() not in ex:
                return False
        if oficio_numero and oficio_numero.strip():
            on = f"{row.get('oficio_numero') or ''}{row.get('oficio_anio') or ''}".lower()
            if oficio_numero.strip().lower() not in on:
                return False
        if estado_recorrido and estado_recorrido.strip():
            if estado_recorrido_label(act).lower() != estado_recorrido.strip().lower():
                return False
        if tipo_final and tipo_final.strip():
            rc = (row.get("resultado_cumplimiento_oficio") or "").strip().upper()
            if rc != tipo_final.strip().upper():
                return False
        return True

    return [a for a in rows if _keep(a)]
