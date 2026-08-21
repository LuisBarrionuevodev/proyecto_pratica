"""
SQL helpers para M4 planificación optimizado (OPER-RUTA.7B).

Filtros server-side: pool/ruta activa (NOT EXISTS) y distrito por domicilio efectivo.
"""

from __future__ import annotations

from sqlalchemy import and_, case, exists, func, literal, or_, select
from sqlalchemy.orm import Query, aliased

from app.models import (
    Actuaciones,
    Comprobacion,
    Denuncia,
    Distrito,
    Domicilio,
    DomicilioGeocode,
    IniciadorRuta,
    Notificacion,
    Oficio,
    Relevamiento,
    RutaItem,
    RutaPoolDia,
    RutaTrabajo,
)

_TIPOS_OFICIO: tuple[str, ...] = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)
_ESTADOS_RUTA_ITEM_ABIERTOS: tuple[str, ...] = (
    "PENDIENTE_ASIGNACION",
    "ASIGNADO",
    "EN_PROCESO",
)
_ESTADOS_RUTA_BLOQUEAN: tuple[str, ...] = (
    "PUBLICADA",
    "EN_CURSO",
    "CERRADA",
    "CANCELADA",
)


def apply_sql_exclusion_pool_y_ruta_activa(query: Query) -> Query:
    """
    Excluye iniciadores no agregables (6I/6J) con NOT EXISTS en SQL.

    Cubre pool EN_POOL, ASIGNADO_A_RUTA con ítem abierto e ítems abiertos en rutas no BORRADOR.
    La exclusión de ítems en ruta BORRADOR sigue en ``planificable_iniciadores_base_query``.
    """
    pool_en_pool = exists(
        select(RutaPoolDia.id).where(
            RutaPoolDia.iniciador_ruta_id == IniciadorRuta.id,
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado == "EN_POOL",
        ).correlate(IniciadorRuta)
    )

    item_abierto = exists(
        select(RutaItem.id).where(
            RutaItem.id == RutaPoolDia.ruta_item_id,
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item.in_(_ESTADOS_RUTA_ITEM_ABIERTOS),
        ).correlate(RutaPoolDia)
    )

    pool_asignado_bloquea = exists(
        select(RutaPoolDia.id).where(
            RutaPoolDia.iniciador_ruta_id == IniciadorRuta.id,
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado == "ASIGNADO_A_RUTA",
            or_(RutaPoolDia.ruta_item_id.is_(None), item_abierto),
        ).correlate(IniciadorRuta)
    )

    ruta_no_borrador_bloquea = exists(
        select(RutaItem.id).where(
            RutaItem.iniciador_ruta_id == IniciadorRuta.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item.in_(_ESTADOS_RUTA_ITEM_ABIERTOS),
            RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta.in_(_ESTADOS_RUTA_BLOQUEAN)),
        ).correlate(IniciadorRuta)
    )

    return query.filter(
        ~pool_en_pool,
        ~pool_asignado_bloquea,
        ~ruta_no_borrador_bloquea,
    )


def _act_notif_domicilio_scalar():
    """Última actuación INSPECCION de la notificación del iniciador."""
    return (
        select(Actuaciones.domicilio_id)
        .where(
            Actuaciones.notificacion_id == IniciadorRuta.notificacion_id,
            Actuaciones.tipo == "INSPECCION",
        )
        .order_by(Actuaciones.id.desc())
        .limit(1)
        .correlate(IniciadorRuta)
        .scalar_subquery()
    )


def _act_comp_domicilio_scalar(oficio_alias: Oficio):
    """Última actuación de la comprobación (directa o vía oficio)."""
    comp_id = func.coalesce(IniciadorRuta.comprobacion_id, oficio_alias.comprobacion_id)
    return (
        select(Actuaciones.domicilio_id)
        .where(Actuaciones.comprobacion_id == comp_id)
        .order_by(Actuaciones.id.desc())
        .limit(1)
        .correlate(IniciadorRuta)
        .correlate(oficio_alias)
        .scalar_subquery()
    )


def _punto_geom_desde_geocode(geo_alias: DomicilioGeocode):
    """WKT POINT(lng lat) desde fila geocode (misma convención que resolve_distrito_id)."""
    point_wkt = func.concat(
        literal("POINT("),
        geo_alias.lng,
        literal(" "),
        geo_alias.lat,
        literal(")"),
    )
    return func.ST_GeomFromText(point_wkt, 4326)


def _distrito_contiene_punto_geocode(geo_alias: DomicilioGeocode, distrito_id: int):
    """
    EXISTS: el punto geocode cae dentro del polígono del distrito.

    Replica ``resolve_distrito_id`` cuando ``domicilio.distrito_id`` aún es NULL
    (path legacy M4 hacía backfill antes del filtro; 7B optimizado no).
    """
    point_geom = _punto_geom_desde_geocode(geo_alias)
    swapped = func.ST_SwapXY(Distrito.geom)
    return exists(
        select(literal(1))
        .select_from(Distrito)
        .where(
            Distrito.id == int(distrito_id),
            Distrito.geom.isnot(None),
            or_(
                func.ST_Contains(swapped, point_geom),
                func.ST_Intersects(swapped, point_geom),
            ),
        )
        .correlate(geo_alias)
    )


def _filtro_distrito_efectivo_clause(dom_efectivo, geo_efectivo, distrito_id: int):
    """
    Coincide con path legacy M4:
    - ``domicilio.distrito_id == distrito`` cuando FK está persistida;
    - si FK es NULL pero hay geocode OK, resuelve por polígono (como backfill + mapa geo).
    """
    fk_match = dom_efectivo.distrito_id == int(distrito_id)
    geo_ok = and_(
        geo_efectivo.domicilio_id.isnot(None),
        geo_efectivo.deleted_at.is_(None),
        geo_efectivo.geo_status == "OK",
        geo_efectivo.lat.isnot(None),
        geo_efectivo.lng.isnot(None),
    )
    spatial_match = and_(
        dom_efectivo.distrito_id.is_(None),
        geo_ok,
        _distrito_contiene_punto_geocode(geo_efectivo, int(distrito_id)),
    )
    return or_(fk_match, spatial_match)


def apply_joins_y_filtro_distrito_efectivo(query: Query, distrito_id: int) -> Query:
    """
    Joins para domicilio efectivo (PR5) y filtro ``distrito_id`` en SQL.

    Replica la prioridad de ``resolve_domicilio_efectivo_para_iniciador`` en lectura.
    """
    dom_ini = aliased(Domicilio)
    dom_origen = aliased(Domicilio)
    dom_efectivo = aliased(Domicilio)

    rel = aliased(Relevamiento)
    den = aliased(Denuncia)
    act_ini = aliased(Actuaciones)
    ofi = aliased(Oficio)

    geo_efectivo = aliased(DomicilioGeocode)

    act_notif_dom = _act_notif_domicilio_scalar()
    act_comp_dom = _act_comp_domicilio_scalar(ofi)

    origen_dom_id = case(
        (IniciadorRuta.tipo_iniciador == "RELEVAMIENTO", rel.domicilio_id),
        (IniciadorRuta.tipo_iniciador == "DENUNCIA", den.domicilio_id),
        (
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            func.coalesce(act_ini.domicilio_id, act_notif_dom),
        ),
        (
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_OFICIO),
            func.coalesce(act_ini.domicilio_id, act_comp_dom),
        ),
        else_=act_ini.domicilio_id,
    )

    ini_dom_active = and_(
        IniciadorRuta.domicilio_id.isnot(None),
        dom_ini.deleted_at.is_(None),
    )
    ini_dom_inactive = or_(
        IniciadorRuta.domicilio_id.is_(None),
        dom_ini.deleted_at.isnot(None),
    )
    origen_dom_active = and_(
        origen_dom_id.isnot(None),
        dom_origen.deleted_at.is_(None),
    )

    effective_dom_id = case(
        (
            and_(
                ini_dom_active,
                or_(
                    origen_dom_id.is_(None),
                    IniciadorRuta.domicilio_id == origen_dom_id,
                    dom_origen.deleted_at.isnot(None),
                ),
            ),
            IniciadorRuta.domicilio_id,
        ),
        (
            and_(
                ini_dom_active,
                origen_dom_id.isnot(None),
                IniciadorRuta.domicilio_id != origen_dom_id,
                origen_dom_active,
            ),
            origen_dom_id,
        ),
        (
            and_(ini_dom_inactive, origen_dom_active),
            origen_dom_id,
        ),
        else_=None,
    )

    query = (
        query.outerjoin(dom_ini, dom_ini.id == IniciadorRuta.domicilio_id)
        .outerjoin(rel, rel.id == IniciadorRuta.relevamiento_id)
        .outerjoin(den, den.id == IniciadorRuta.denuncia_id)
        .outerjoin(act_ini, act_ini.id == IniciadorRuta.actuacion_id)
        .outerjoin(ofi, ofi.id == IniciadorRuta.oficio_id)
        .outerjoin(dom_origen, dom_origen.id == origen_dom_id)
        .outerjoin(dom_efectivo, dom_efectivo.id == effective_dom_id)
        .outerjoin(
            geo_efectivo,
            and_(
                geo_efectivo.domicilio_id == dom_efectivo.id,
                geo_efectivo.deleted_at.is_(None),
                geo_efectivo.geo_status == "OK",
                geo_efectivo.lat.isnot(None),
                geo_efectivo.lng.isnot(None),
            ),
        )
        .filter(_filtro_distrito_efectivo_clause(dom_efectivo, geo_efectivo, int(distrito_id)))
    )
    return query
