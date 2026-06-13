"""
Filtros de texto/tipo para bandeja urgentes (M3).
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.models import Comprobacion, Domicilio, Distrito, IniciadorRuta, Notificacion, Oficio, Rubro

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
    q_identificador: str | None = None,
    q_domicilio: str | None = None,
    rubro_id: int | None = None,
) -> Query:
    """
    Aplica filtros opcionales sobre query base de urgentes (ya acotada a elegible_urgente).

    Parámetros:
        tipo_urgente: DENUNCIA | NOTIFICACION | OFICIO
        q: búsqueda libre legacy (domicilio, rubro, distrito, números)
        numero_oficio / numero_comprobacion: filtros legacy por número
        q_identificador: oficio, comprobación o notificación (numero_acta)
        q_domicilio: domicilio / calle / observaciones
        rubro_id: filtro exacto por domicilio.rubro_id

    Retorno:
        Query con joins/filtros aplicados (`.distinct()` al final).
    """
    tipo = (_strip_or_none(tipo_urgente) or "").upper() or None
    if tipo == "DENUNCIA":
        query = query.filter(IniciadorRuta.tipo_iniciador == "DENUNCIA")
    elif tipo == "NOTIFICACION":
        query = query.filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION")
    elif tipo == "OFICIO":
        query = query.filter(IniciadorRuta.tipo_iniciador.in_(TIPOS_OFICIO_URGENTE))

    if rubro_id is not None:
        query = query.filter(Domicilio.rubro_id == rubro_id)

    num_oficio = _strip_or_none(numero_oficio)
    num_comp = _strip_or_none(numero_comprobacion)
    q_term = _strip_or_none(q)
    q_id = _strip_or_none(q_identificador)
    q_dom = _strip_or_none(q_domicilio)

    needs_oficio_join = bool(num_oficio or q_term or q_id)
    needs_comp_join = bool(num_comp or q_term or q_id)
    needs_noti_join = bool(q_id)
    needs_rubro_join = bool(q_term)
    needs_distrito_join = bool(q_term)

    if needs_oficio_join:
        query = query.outerjoin(Oficio, Oficio.id == IniciadorRuta.oficio_id)
    if needs_comp_join:
        query = query.outerjoin(Comprobacion, Comprobacion.id == IniciadorRuta.comprobacion_id)
    if needs_noti_join:
        query = query.outerjoin(Notificacion, Notificacion.id == IniciadorRuta.notificacion_id)
    if needs_rubro_join:
        query = query.outerjoin(Rubro, Rubro.id == Domicilio.rubro_id)
    if needs_distrito_join:
        query = query.outerjoin(Distrito, Distrito.id == Domicilio.distrito_id)

    if num_oficio:
        query = query.filter(Oficio.numero_oficio.ilike(f"%{num_oficio}%"))
    if num_comp:
        query = query.filter(Comprobacion.numero_acta.ilike(f"%{num_comp}%"))

    if q_id:
        term_id = f"%{q_id}%"
        query = query.filter(
            or_(
                Oficio.numero_oficio.ilike(term_id),
                Comprobacion.numero_acta.ilike(term_id),
                Notificacion.numero_acta.ilike(term_id),
            )
        )

    if q_dom:
        term_dom = f"%{q_dom}%"
        query = query.filter(
            or_(
                Domicilio.calle.ilike(term_dom),
                Domicilio.numero.ilike(term_dom),
                IniciadorRuta.observaciones.ilike(term_dom),
            )
        )

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
