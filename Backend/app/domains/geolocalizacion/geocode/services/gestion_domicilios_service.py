"""
Servicio Gestión Domicilios — cola operativa geográfica (PR6C.3).

Query paginada sobre ``domicilio`` + ``domicilio_geocode`` sin ``match_calle`` masivo.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, case, func, or_

from app.database import db
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_query import (
    GestionDomiciliosQuery,
    StatusOperativoFilter,
)
from app.domains.geolocalizacion.geocode.schemas.gestion_domicilios_response import (
    GestionDomiciliosMapPointOut,
    GestionDomiciliosPaginationOut,
    GestionDomiciliosResponse,
    GestionDomiciliosRowOut,
    GestionDomiciliosRowTecnicoOut,
    GestionDomiciliosSummaryOut,
)
from app.domains.geolocalizacion.geocode.services.domicilio_clasificacion_service import (
    clasificar_domicilio,
)
from app.domains.geolocalizacion.geocode.services.gestion_domicilios_status import (
    STATUS_LABELS,
    requiere_accion,
    resolve_geo_chip,
    resolve_status_operativo,
    status_operativo_sql_case,
)
from app.models import CalleCatalogo, Domicilio, DomicilioGeocode
from app.shared.perf_log import PerfTimer, perf_endpoint_log, perf_log_enabled

MAP_POINTS_LIMIT = 200
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class GestionDomiciliosPerfStats:
    """Métricas de la última ejecución (benchmark / PERF_LOG)."""

    rows_sql: int = 0
    rows_response: int = 0
    map_points: int = 0
    query_ms: float = 0.0
    summary_ms: float = 0.0
    total_ms: float = 0.0
    status_operativo: str | None = None


_last_gestion_domicilios_perf = GestionDomiciliosPerfStats()


def get_last_gestion_domicilios_perf() -> GestionDomiciliosPerfStats:
    """Devuelve métricas de la última llamada a ``list_gestion_domicilios``."""
    return _last_gestion_domicilios_perf


def _effective_page_size(page_size: int) -> int:
    return max(1, min(int(page_size), MAX_PAGE_SIZE))


def _format_domicilio_linea(dom: Domicilio) -> str:
    calle = (dom.calle_normalizada or dom.calle or "").strip()
    if (dom.numero_tipo or "").strip().upper() == "ESQUINA":
        esquina = (dom.esquina_normalizada or dom.esquina_raw or "").strip()
        if esquina and calle:
            return f"{calle} y {esquina}"
        return esquina or calle
    numero = (dom.numero or "").strip()
    if calle and numero:
        return f"{calle} {numero}"
    return calle or numero or f"Domicilio #{dom.id}"


def _calle_sugerida(dom: Domicilio, catalogo: CalleCatalogo | None) -> str | None:
    if dom.calle_normalizada:
        return dom.calle_normalizada.strip() or None
    if catalogo and catalogo.nombre_canonico:
        return catalogo.nombre_canonico.strip()
    return None


def _apply_search_filter(query, q_text: str | None):
    if not q_text or not q_text.strip():
        return query
    term = f"%{q_text.strip()}%"
    return query.filter(
        or_(
            Domicilio.calle.like(term),
            Domicilio.calle_normalizada.like(term),
            Domicilio.numero.like(term),
        )
    )


def _build_base_query(q_text: str | None):
    query = (
        db.session.query(Domicilio, DomicilioGeocode, CalleCatalogo)
        .outerjoin(
            DomicilioGeocode,
            and_(
                Domicilio.id == DomicilioGeocode.domicilio_id,
                DomicilioGeocode.deleted_at.is_(None),
            ),
        )
        .outerjoin(CalleCatalogo, Domicilio.calle_catalogo_id == CalleCatalogo.id)
        .filter(Domicilio.deleted_at.is_(None))
    )
    return _apply_search_filter(query, q_text)


def _apply_status_filter(query, status_filter: StatusOperativoFilter):
    status_expr = status_operativo_sql_case()
    if status_filter == "todos":
        return query
    if status_filter == "requiere_accion":
        return query.filter(status_expr.in_(["sin_punto", "punto_dudoso", "error"]))
    return query.filter(status_expr == status_filter)


def _build_summary(q_text: str | None) -> GestionDomiciliosSummaryOut:
    status_expr = status_operativo_sql_case()
    row = (
        _build_base_query(q_text)
        .with_entities(
            func.count(Domicilio.id).label("total"),
            func.sum(case((status_expr == "sin_punto", 1), else_=0)).label("sin_punto"),
            func.sum(case((status_expr == "punto_dudoso", 1), else_=0)).label("punto_dudoso"),
            func.sum(case((status_expr == "error", 1), else_=0)).label("errores"),
            func.sum(case((status_expr == "manual", 1), else_=0)).label("manuales"),
            func.sum(case((status_expr == "geolocalizado", 1), else_=0)).label("geolocalizados"),
        )
        .one()
    )
    sin_punto = int(row.sin_punto or 0)
    punto_dudoso = int(row.punto_dudoso or 0)
    errores = int(row.errores or 0)
    return GestionDomiciliosSummaryOut(
        total=int(row.total or 0),
        requieren_accion=sin_punto + punto_dudoso + errores,
        sin_punto=sin_punto,
        punto_dudoso=punto_dudoso,
        errores=errores,
        manuales=int(row.manuales or 0),
        geolocalizados=int(row.geolocalizados or 0),
    )


def _apply_sort(query, sort: str):
    status_expr = status_operativo_sql_case()
    if sort == "updated_desc":
        return query.order_by(Domicilio.updated_at.desc(), Domicilio.id.desc())
    if sort == "domicilio_asc":
        return query.order_by(Domicilio.calle.asc(), Domicilio.numero.asc(), Domicilio.id.asc())
    req_first = case(
        (status_expr.in_(["sin_punto", "punto_dudoso", "error"]), 0),
        else_=1,
    )
    return query.order_by(req_first.asc(), Domicilio.updated_at.desc(), Domicilio.id.desc())


def _row_to_out(
    dom: Domicilio,
    geo: DomicilioGeocode | None,
    catalogo: CalleCatalogo | None,
    *,
    include_tecnico: bool,
) -> GestionDomiciliosRowOut:
    status = resolve_status_operativo(dom, geo)
    geo_chip, has_coords = resolve_geo_chip(geo)
    lat = float(geo.lat) if geo is not None and geo.lat is not None else None
    lng = float(geo.lng) if geo is not None and geo.lng is not None else None
    tecnico: GestionDomiciliosRowTecnicoOut | None = None
    if include_tecnico:
        clasif = clasificar_domicilio(dom, geo=geo)
        tecnico = GestionDomiciliosRowTecnicoOut(
            score_unificado=clasif.get("score_unificado"),
            match_strategy=None,
            confidence_reason=None,
            nomenclatura_estado=clasif.get("nomenclatura_estado"),
            geocode_estado=clasif.get("geocode_estado"),
            motivos=clasif.get("motivos"),
        )
    return GestionDomiciliosRowOut(
        domicilio_id=int(dom.id),
        domicilio_linea=_format_domicilio_linea(dom),
        calle_sugerida=_calle_sugerida(dom, catalogo),
        referencia_breve=STATUS_LABELS.get(status, status),
        status_operativo=status,  # type: ignore[arg-type]
        status_operativo_label=STATUS_LABELS.get(status, status),
        geo_chip=geo_chip,  # type: ignore[arg-type]
        has_coordinates=has_coords,
        lat=lat,
        lng=lng,
        requiere_accion=requiere_accion(status),
        tecnico=tecnico,
    )


def _map_points_for_filter(
    query: GestionDomiciliosQuery,
) -> list[GestionDomiciliosMapPointOut]:
    status_expr = status_operativo_sql_case()
    q = _apply_status_filter(_build_base_query(query.q), query.status_operativo)
    has_coords = and_(
        DomicilioGeocode.lat.isnot(None),
        DomicilioGeocode.lng.isnot(None),
    )
    q = q.filter(has_coords)

    if query.map_mode == "problematic":
        q = q.filter(status_expr.in_(["sin_punto", "punto_dudoso", "error", "manual"]))
    elif query.map_mode == "visible":
        q = q.filter(status_expr.in_(["punto_dudoso", "manual", "geolocalizado"]))

    rows = q.order_by(Domicilio.updated_at.desc(), Domicilio.id.desc()).limit(MAP_POINTS_LIMIT).all()
    points: list[GestionDomiciliosMapPointOut] = []
    for dom, geo, _catalogo in rows:
        if geo is None:
            continue
        status = resolve_status_operativo(dom, geo)
        points.append(
            GestionDomiciliosMapPointOut(
                domicilio_id=int(dom.id),
                lat=float(geo.lat),
                lng=float(geo.lng),
                status_operativo=status,  # type: ignore[arg-type]
                label=_format_domicilio_linea(dom),
            )
        )
    return points


def list_gestion_domicilios(query: GestionDomiciliosQuery) -> GestionDomiciliosResponse:
    """
    Lista paginada de domicilios para Gestión Domicilios v1.

    Parámetros:
        query: filtros, paginación y flags validados.

    Retorno:
        Summary, filas paginadas, map_points opcionales y paginación.

    Errores:
        Ninguno en flujo normal; validación ocurre en la ruta vía Pydantic.
    """
    global _last_gestion_domicilios_perf

    total_timer = PerfTimer()
    page_size = _effective_page_size(query.page_size)
    page = max(1, int(query.page))

    summary_timer = PerfTimer()
    summary = _build_summary(query.q)
    summary_ms = summary_timer.elapsed_ms()

    filtered = _apply_status_filter(_build_base_query(query.q), query.status_operativo)

    count_timer = PerfTimer()
    total = filtered.count()
    count_ms = count_timer.elapsed_ms()

    page_query = _apply_sort(filtered, query.sort)
    fetch_timer = PerfTimer()
    sql_rows = page_query.offset((page - 1) * page_size).limit(page_size).all()
    fetch_ms = fetch_timer.elapsed_ms()

    rows = [
        _row_to_out(dom, geo, catalogo, include_tecnico=query.include_tecnico)
        for dom, geo, catalogo in sql_rows
    ]

    map_points: list[GestionDomiciliosMapPointOut] = []
    if query.include_map_points:
        map_points = _map_points_for_filter(query)

    total_ms = total_timer.elapsed_ms()
    _last_gestion_domicilios_perf = GestionDomiciliosPerfStats(
        rows_sql=len(sql_rows),
        rows_response=len(rows),
        map_points=len(map_points),
        query_ms=count_ms + fetch_ms,
        summary_ms=summary_ms,
        total_ms=total_ms,
        status_operativo=query.status_operativo,
    )

    response = GestionDomiciliosResponse(
        summary=summary,
        rows=rows,
        map_points=map_points,
        pagination=GestionDomiciliosPaginationOut(
            page=page,
            page_size=page_size,
            total=int(total),
        ),
    )

    if perf_log_enabled():
        perf_endpoint_log(
            "map.gestion_domicilios",
            rows_base=len(sql_rows),
            rows_final=len(rows),
            query_ms=count_ms + fetch_ms,
            presenter_ms=summary_ms,
            total_ms=total_ms,
            payload=response.model_dump(mode="json"),
            map_points=len(map_points),
            status_operativo=query.status_operativo,
            page=page,
            page_size=page_size,
        )

    return response
