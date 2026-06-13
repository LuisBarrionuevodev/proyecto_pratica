"""
Filtros de texto/tipo para bandeja urgentes (M3).
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.models import Comprobacion, Domicilio, Distrito, IniciadorRuta, Oficio, Rubro

TIPOS_OFICIO_URGENTE: tuple[str, ...] = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

TipoUrgenteLiteral = str | None


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def apply_urgentes_filtros(
    query: Query,
    *,
    tipo_urgente: TipoUrgenteLiteral = None,
    q: str | None = None,
    numero_oficio: str | None = None,
    numero_comprobacion: str | None = None,
) -> Query:
    """
    Aplica filtros opcionales sobre query base de urgentes (ya acotada a elegible_urgente).

    Parámetros:
        tipo_urgente: DENUNCIA | NOTIFICACION | OFICIO
        q: búsqueda libre (domicilio, rubro, distrito, números de oficio/comprobación)
        numero_oficio: filtro por número de oficio
        numero_comprobacion: filtro por número de acta de comprobación

    Retorno:
        Query con joins/filtros aplicados (puede requerir `.distinct()` en count).
    """
    tipo = (_strip_or_none(tipo_urgente) or "").upper() or None
    if tipo == "DENUNCIA":
        query = query.filter(IniciadorRuta.tipo_iniciador == "DENUNCIA")
    elif tipo == "NOTIFICACION":
        query = query.filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
    elif tipo == "OFICIO":
        query = query.filter(IniciadorRuta.tipo_iniciador.in_(TIPOS_OFICIO_URGENTE))

    num_oficio = _strip_or_none(numero_oficio)
    num_comp = _strip_or_none(numero_comprobacion)
    q_term = _strip_or_none(q)

    needs_oficio_join = bool(num_oficio or q_term)
    needs_comp_join = bool(num_comp or q_term)
    needs_rubro_join = bool(q_term)
    needs_distrito_join = bool(q_term)

    if needs_oficio_join:
        query = query.outerjoin(Oficio, Oficio.id == IniciadorRuta.oficio_id)
    if needs_comp_join:
        query = query.outerjoin(Comprobacion, Comprobacion.id == IniciadorRuta.comprobacion_id)
    if needs_rubro_join:
        query = query.outerjoin(Rubro, Rubro.id == Domicilio.rubro_id)
    if needs_distrito_join:
        query = query.outerjoin(Distrito, Distrito.id == Domicilio.distrito_id)

    if num_oficio:
        query = query.filter(Oficio.numero_oficio.ilike(f"%{num_oficio}%"))
    if num_comp:
        query = query.filter(Comprobacion.numero_acta.ilike(f"%{num_comp}%"))

    if q_term:
        term = f"%{q_term}%"
        query = query.filter(
            or_(
                Domicilio.calle.ilike(term),
                Domicilio.numero.ilike(term),
                IniciadorRuta.observaciones.ilike(term),
                Rubro.nombre.ilike(term),
                Distrito.nombre.ilike(term),
                Oficio.numero_oficio.ilike(term),
                Comprobacion.numero_acta.ilike(term),
            )
        )

    return query.distinct()
