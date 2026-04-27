"""
Bandejas operativas unificadas para actas de comprobación (oficio / reinspección / recorrido).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.database import db
from app.domains.actuaciones.services.pendientes_service import _apply_distrito_optional, _apply_fecha
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import estado_recorrido_label
from app.models import Actuaciones, IniciadorRuta
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters

_REINSPECCION_OFICIO_TERMINAL: tuple[str, ...] = ("CUMPLIDO",) + tuple(inactive_estados())


def list_pendientes_reinspeccion_oficio(
    filters: ActuacionesPendientesFilters,
) -> List[Tuple[IniciadorRuta, Actuaciones]]:
    """
    Iniciadores ``REINSPECCION_OFICIO`` aún pendientes de cierre operativo.

    Cada fila es (iniciador, actuación ancla). Rango de fechas sobre ``Actuaciones.fecha``.

    Importante: usar ``query(IniciadorRuta, Actuaciones)`` para devolver tuplas; ``IniciadorRuta.query.join`` solo
    devolvía iniciadores y el route desempaquetaba mal (``iniciador_reinspeccion_to_row`` fallaba).
    """
    q = (
        db.session.query(IniciadorRuta, Actuaciones)
        .join(Actuaciones, Actuaciones.id == IniciadorRuta.actuacion_id)
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .filter(~IniciadorRuta.estado_iniciador.in_(_REINSPECCION_OFICIO_TERMINAL))
    )
    q = _apply_fecha(q, filters.desde, filters.hasta)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    return q.order_by(IniciadorRuta.id.desc()).all()


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
