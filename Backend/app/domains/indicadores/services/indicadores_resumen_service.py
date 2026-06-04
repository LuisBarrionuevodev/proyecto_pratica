from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import and_, exists, extract, func

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    _loose_key,
)
from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _realizados_inspector_coincide,
    count_mapa_operativo_pendientes_cola,
    count_mapa_operativo_pendientes_en_ruta,
    count_mapa_operativo_realizados_visita,
)
from app.domains.indicadores.schemas.resumen_out import (
    ActasLabradasMesItem,
    ActasPorTipo,
    ActuacionPorTipoOperativoItem,
    ActuacionesResumen,
    ContraproducenciaPorTipoItem,
    ContraproducenciaTopItem,
    DecomisoKgPorMesItem,
    DecomisoKgResumen,
    IndicadoresResumenOut,
    MapaOperativoResumen,
    RankingInspectorItem,
    ReinspeccionesRealizadas,
    RubroTopItem,
    RutaItemsEjecucionResumen,
)
from app.models import (
    Actuaciones,
    Clausura,
    Comprobacion,
    Decomiso,
    Domicilio,
    IniciadorRuta,
    Inspeccion,
    Inspector,
    Motivo,
    Rubro,
    RutaItem,
    RutaTrabajo,
    actuaciones_inspector,
)
from app.models.notificacion_motivo import notificacion_motivo

_TOP_RUBROS_LIMIT = 10
_TOP_MOTIVOS_LIMIT = 10
_RANKING_INSPECTORES_LIMIT = 15
_TOP_CONTRAPRODUCCIONES_LIMIT = 10
_SIN_RUBRO_LABEL = "Sin rubro"
_COMP_MOTIVO_PENDIENTE_KEYS = frozenset({_loose_key("PENDIENTE")})

# Valores excluidos del top de contraproducencias (bloque no-realizadas).
_CONTRAP_EXCLUIDAS_TOP = frozenset(
    {
        _loose_key("NO_HUBO"),
        _loose_key("NO HUBO"),
    }
)

_TIPOS_INICIADOR_VISITA_REALIZADA = (
    "REINSPECCION_NOTIFICACION",
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)


def _float_kg(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def _normalize_motivo_label(raw: str) -> str:
    """
    Etiqueta legible para motivos (trim, espacios).

    Reemplaza ``_`` por espacio solo en enums tipo ``SNAKE_CASE`` / MAYÚSCULAS.
    """
    s = " ".join(str(raw).strip().split())
    if "_" in s and " " not in s and (s.isupper() or s.upper() == s):
        s = s.replace("_", " ")
    return s


def _actuacion_ids_subquery(
    desde: date,
    hasta: date,
    distrito_id: Optional[int],
    inspector_id: Optional[int],
):
    """
    Subconsulta de IDs de actuaciones en rango de fecha con filtros opcionales.

    Parámetros:
        desde, hasta: rango inclusive sobre `Actuaciones.fecha`.
        distrito_id: join por domicilio; excluye actuaciones sin domicilio o de otro distrito.
        inspector_id: join por `actuaciones_inspector` con `deleted_at` nulo.

    Retorno:
        Subquery con columna `id`.
    """
    q = db.session.query(Actuaciones.id).filter(
        Actuaciones.fecha >= desde,
        Actuaciones.fecha <= hasta,
    )
    if distrito_id is not None:
        q = q.join(Domicilio, Domicilio.id == Actuaciones.domicilio_id).filter(
            Domicilio.distrito_id == distrito_id
        )
    if inspector_id is not None:
        q = q.join(
            actuaciones_inspector,
            actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
        ).filter(
            actuaciones_inspector.c.inspector_id == inspector_id,
            actuaciones_inspector.c.deleted_at.is_(None),
        )
    return q.distinct().subquery("act_indicadores_filtered")


def _has_contraproducencia_expr():
    return and_(
        Actuaciones.contraproducencia.isnot(None),
        func.trim(Actuaciones.contraproducencia) != "",
    )


def _notificacion_labarda_exists():
    """
    Subquery: la actuación tiene notificación con al menos un motivo cargado.

    Excluye previas documentales (notificación sin filas en `notificacion_motivo`).
    """
    return exists().where(
        notificacion_motivo.c.notificacion_id == Actuaciones.notificacion_id,
        notificacion_motivo.c.deleted_at.is_(None),
    )


def _comprobacion_labarda_filter():
    """
    Filtro de comprobación labrada en la visita (no previa/origen).

    Previas usan motivo placeholder ``PENDIENTE`` en ``previas_service``.
    """
    return and_(
        Actuaciones.comprobacion_id.isnot(None),
        exists().where(
            Comprobacion.id == Actuaciones.comprobacion_id,
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.isnot(None),
            func.trim(Comprobacion.motivo) != "",
            Comprobacion.motivo != "PENDIENTE",
        ),
    )


def _count_actas_labradas(sq) -> ActasPorTipo:
    """Cuenta actas labradas (no referencias) en el conjunto filtrado."""
    n_insp = (
        db.session.query(func.count(Inspeccion.id))
        .join(sq, sq.c.id == Inspeccion.actuacion_id)
        .scalar()
        or 0
    )
    n_notif = (
        db.session.query(func.count(func.distinct(Actuaciones.id)))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Actuaciones.notificacion_id.isnot(None),
            _notificacion_labarda_exists(),
        )
        .scalar()
        or 0
    )
    n_comp = (
        db.session.query(func.count(func.distinct(Actuaciones.id)))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(_comprobacion_labarda_filter())
        .scalar()
        or 0
    )
    n_clau = (
        db.session.query(func.count(Clausura.id))
        .join(sq, sq.c.id == Clausura.actuacion_id)
        .scalar()
        or 0
    )
    n_deco = (
        db.session.query(func.count(Decomiso.id))
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .scalar()
        or 0
    )
    return ActasPorTipo(
        inspeccion=int(n_insp),
        notificacion=int(n_notif),
        comprobacion=int(n_comp),
        clausura=int(n_clau),
        decomiso=int(n_deco),
    )


def _iter_months_in_range(desde: date, hasta: date):
    y, m = desde.year, desde.month
    end_y, end_m = hasta.year, hasta.month
    while (y, m) <= (end_y, end_m):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _monthly_acta_counts(sq, acta_kind: str) -> dict[tuple[int, int], int]:
    """
    Agrega conteos por año-mes de fecha de actuación para un tipo de acta labrada.

    Parámetros:
        sq: subquery de actuaciones filtradas.
        acta_kind: ``inspeccion`` | ``notificacion`` | ``comprobacion`` | ``clausura`` | ``decomiso``.

    Retorno:
        Mapa ``(anio, mes) -> count``.
    """
    ym = (
        extract("year", Actuaciones.fecha).label("anio"),
        extract("month", Actuaciones.fecha).label("mes"),
    )
    if acta_kind == "inspeccion":
        q = (
            db.session.query(*ym, func.count(Inspeccion.id))
            .join(Inspeccion, Inspeccion.actuacion_id == Actuaciones.id)
            .join(sq, sq.c.id == Actuaciones.id)
        )
    elif acta_kind == "notificacion":
        q = (
            db.session.query(*ym, func.count(func.distinct(Actuaciones.id)))
            .join(sq, sq.c.id == Actuaciones.id)
            .filter(
                Actuaciones.notificacion_id.isnot(None),
                _notificacion_labarda_exists(),
            )
        )
    elif acta_kind == "comprobacion":
        q = (
            db.session.query(*ym, func.count(func.distinct(Actuaciones.id)))
            .join(sq, sq.c.id == Actuaciones.id)
            .filter(_comprobacion_labarda_filter())
        )
    elif acta_kind == "clausura":
        q = (
            db.session.query(*ym, func.count(Clausura.id))
            .join(Clausura, Clausura.actuacion_id == Actuaciones.id)
            .join(sq, sq.c.id == Actuaciones.id)
        )
    elif acta_kind == "decomiso":
        q = (
            db.session.query(*ym, func.count(Decomiso.id))
            .join(Decomiso, Decomiso.actuacion_id == Actuaciones.id)
            .join(sq, sq.c.id == Actuaciones.id)
        )
    else:
        raise ValueError(f"Tipo de acta desconocido: {acta_kind}")

    rows = q.group_by(*ym).all()
    return {(int(y), int(m)): int(c) for y, m, c in rows}


def _actas_labradas_mensual(
    sq,
    desde: date,
    hasta: date,
) -> list[ActasLabradasMesItem]:
    """Serie mensual de actas labradas (sin previas/origen) en el conjunto filtrado."""
    by_kind = {
        kind: _monthly_acta_counts(sq, kind)
        for kind in ("inspeccion", "notificacion", "comprobacion", "clausura", "decomiso")
    }
    out: list[ActasLabradasMesItem] = []
    for anio, mes in _iter_months_in_range(desde, hasta):
        key = (anio, mes)
        inspeccion = by_kind["inspeccion"].get(key, 0)
        notificacion = by_kind["notificacion"].get(key, 0)
        comprobacion = by_kind["comprobacion"].get(key, 0)
        clausura = by_kind["clausura"].get(key, 0)
        decomiso = by_kind["decomiso"].get(key, 0)
        total = inspeccion + notificacion + comprobacion + clausura + decomiso
        if total == 0:
            continue
        out.append(
            ActasLabradasMesItem(
                anio=anio,
                mes=mes,
                total=total,
                inspeccion=inspeccion,
                notificacion=notificacion,
                comprobacion=comprobacion,
                clausura=clausura,
                decomiso=decomiso,
            )
        )
    return out


def _ranking_inspectores(sq) -> list[RankingInspectorItem]:
    """Actuaciones del periodo agrupadas por inspector interviniente."""
    rows = (
        db.session.query(
            Inspector.id,
            Inspector.nombre,
            func.count(func.distinct(actuaciones_inspector.c.actuaciones_id)),
        )
        .join(
            actuaciones_inspector,
            actuaciones_inspector.c.inspector_id == Inspector.id,
        )
        .join(sq, sq.c.id == actuaciones_inspector.c.actuaciones_id)
        .filter(actuaciones_inspector.c.deleted_at.is_(None))
        .group_by(Inspector.id, Inspector.nombre)
        .order_by(func.count(func.distinct(actuaciones_inspector.c.actuaciones_id)).desc())
        .limit(_RANKING_INSPECTORES_LIMIT)
        .all()
    )
    return [
        RankingInspectorItem(
            inspector_id=int(iid),
            inspector_nombre=str(nombre),
            total_actuaciones=int(cnt),
        )
        for iid, nombre, cnt in rows
    ]


def count_actuaciones_realizadas_visita(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> int:
    """
    Actuaciones con visita realizada (mapa operativo): FINALIZADO + REALIZADO, ruta PUBLICADA.

    Parámetros:
        desde, hasta: rango inclusive sobre fecha de cierre de ruta.
        distrito_id, inspector_id: filtros opcionales (misma semántica que mapa D1).

    Retorno:
        Cantidad de ítems de ruta cerrados con actuación vinculada.
    """
    return count_mapa_operativo_realizados_visita(
        desde=desde.isoformat(),
        hasta=hasta.isoformat(),
        distrito_id=distrito_id,
        tipo=None,
        inspector_id=inspector_id,
    )


def visitas_realizadas_por_tipo_iniciador(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> dict[str, int]:
    """
    Cuenta visitas realizadas agrupadas por ``IniciadorRuta.tipo_iniciador``.

    Incluye reinspecciones, verificar e informar y ratificaciones de oficio.
    Misma base que ``_reinspecciones_realizadas`` (fecha de cierre en rango).
    """
    fecha_cierre = func.coalesce(func.date(RutaItem.ejecutado_at), RutaTrabajo.fecha)
    q = (
        db.session.query(IniciadorRuta.tipo_iniciador, func.count(func.distinct(IniciadorRuta.id)))
        .select_from(RutaItem)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
            RutaTrabajo.estado_ruta == "PUBLICADA",
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_INICIADOR_VISITA_REALIZADA),
            fecha_cierre >= desde,
            fecha_cierre <= hasta,
        )
    )
    if distrito_id is not None:
        q = q.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id).filter(
            Domicilio.distrito_id == distrito_id,
            Domicilio.deleted_at.is_(None),
        )
    if inspector_id is not None:
        q = q.filter(_realizados_inspector_coincide(inspector_id))

    rows = q.group_by(IniciadorRuta.tipo_iniciador).all()
    return {str(tipo): int(cnt) for tipo, cnt in rows}


def top_contraproducencias_sin_no_hubo(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_CONTRAPRODUCCIONES_LIMIT,
) -> list[tuple[str, int]]:
    """
    Top contraproducencias en actuaciones del periodo, excluyendo NO_HUBO y equivalentes.

    Parámetros:
        desde, hasta, distrito_id, inspector_id: mismo filtro que resumen de actuaciones.
        limit: máximo de filas.

    Retorno:
        Lista de (label normalizado, count) ordenada por frecuencia descendente.
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    has_contra = _has_contraproducencia_expr()
    rows = (
        db.session.query(Actuaciones.contraproducencia, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .group_by(Actuaciones.contraproducencia)
        .order_by(func.count(Actuaciones.id).desc())
        .all()
    )
    out: list[tuple[str, int]] = []
    for valor, cnt in rows:
        label = str(valor).strip()
        if _loose_key(label) in _CONTRAP_EXCLUIDAS_TOP:
            continue
        out.append((label, int(cnt)))
        if len(out) >= limit:
            break
    return out


def query_top_rubros_actuaciones(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_RUBROS_LIMIT,
) -> list[tuple[int, str, int]]:
    """
    Top rubros por cantidad de actuaciones en el periodo (con domicilio y rubro).

    Retorno:
        Lista de (rubro_id, nombre, count).
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    rows = (
        db.session.query(Rubro.id, Rubro.nombre, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .join(Rubro, Rubro.id == Domicilio.rubro_id)
        .group_by(Rubro.id, Rubro.nombre)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(limit)
        .all()
    )
    return [(int(rid), str(nombre), int(cnt)) for rid, nombre, cnt in rows]


def query_top_motivos_notificacion(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_MOTIVOS_LIMIT,
) -> list[tuple[str, int]]:
    """
    Top motivos de notificaciones labradas (cada fila de ``notificacion_motivo`` cuenta).

    Parámetros:
        desde, hasta, distrito_id, inspector_id: mismos filtros que actuaciones del periodo.

    Retorno:
        Lista de (nombre catálogo, ocurrencias) ordenada por frecuencia.
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    rows = (
        db.session.query(Motivo.nombre, func.count(notificacion_motivo.c.motivo))
        .select_from(notificacion_motivo)
        .join(Actuaciones, Actuaciones.notificacion_id == notificacion_motivo.c.notificacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .join(Motivo, Motivo.id == notificacion_motivo.c.motivo)
        .filter(
            notificacion_motivo.c.deleted_at.is_(None),
            Actuaciones.notificacion_id.isnot(None),
            Motivo.nombre.isnot(None),
            func.trim(Motivo.nombre) != "",
        )
        .group_by(Motivo.id, Motivo.nombre)
        .order_by(func.count(notificacion_motivo.c.motivo).desc())
        .limit(limit)
        .all()
    )
    return [(_normalize_motivo_label(nombre), int(cnt)) for nombre, cnt in rows]


def query_top_motivos_comprobacion(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
    *,
    limit: int = _TOP_MOTIVOS_LIMIT,
) -> list[tuple[str, int]]:
    """
    Top motivos de comprobaciones labradas (excluye ``PENDIENTE`` y vacíos).

    Agrupa por etiqueta normalizada para unificar variantes de texto.
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    rows = (
        db.session.query(Comprobacion.motivo, func.count(Comprobacion.id))
        .join(Actuaciones, Actuaciones.comprobacion_id == Comprobacion.id)
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(
            Comprobacion.deleted_at.is_(None),
            Comprobacion.motivo.isnot(None),
            func.trim(Comprobacion.motivo) != "",
            func.upper(func.trim(Comprobacion.motivo)) != "PENDIENTE",
        )
        .group_by(Comprobacion.motivo)
        .all()
    )
    merged: dict[str, int] = {}
    for raw, cnt in rows:
        if _loose_key(str(raw)) in _COMP_MOTIVO_PENDIENTE_KEYS:
            continue
        label = _normalize_motivo_label(str(raw))
        if not label:
            continue
        merged[label] = merged.get(label, 0) + int(cnt)
    return sorted(merged.items(), key=lambda item: item[1], reverse=True)[:limit]


def query_decomiso_kg_por_rubro(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> list[tuple[str, float]]:
    """
    Suma ``decomiso.cantidad`` (kg) por rubro del domicilio de la actuación.

    Actuaciones sin rubro se agrupan en ``Sin rubro``.
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    rubro_label = func.coalesce(Rubro.nombre, _SIN_RUBRO_LABEL)
    rows = (
        db.session.query(rubro_label, func.sum(Decomiso.cantidad))
        .select_from(Decomiso)
        .join(Actuaciones, Actuaciones.id == Decomiso.actuacion_id)
        .join(sq, sq.c.id == Actuaciones.id)
        .outerjoin(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .outerjoin(Rubro, Rubro.id == Domicilio.rubro_id)
        .filter(Decomiso.cantidad.isnot(None))
        .group_by(rubro_label)
        .order_by(func.sum(Decomiso.cantidad).desc())
        .all()
    )
    out: list[tuple[str, float]] = []
    for rubro, kg in rows:
        val = _float_kg(kg)
        if val > 0:
            out.append((str(rubro), val))
    return out


def _reinspecciones_realizadas(
    desde: date,
    hasta: date,
    distrito_id: Optional[int],
    inspector_id: Optional[int],
) -> ReinspeccionesRealizadas:
    """
    Reinspecciones efectivamente realizadas (visita cerrada con actuación).

    Criterio alineado al mapa operativo: ``FINALIZADO`` + ``REALIZADO``, ruta ``PUBLICADA``,
    ``actuacion_id`` no nulo, fecha de cierre ``coalesce(date(ejecutado_at), ruta.fecha)`` en rango.
    """
    por_tipo = visitas_realizadas_por_tipo_iniciador(
        desde, hasta, distrito_id, inspector_id
    )
    return ReinspeccionesRealizadas(
        notificacion=por_tipo.get("REINSPECCION_NOTIFICACION", 0),
        oficio=por_tipo.get("REINSPECCION_OFICIO", 0),
    )


def _contraproducencias_por_tipo(sq, total: int) -> list[ContraproducenciaPorTipoItem]:
    """Distribución completa por valor de contraproducencia (incluye sin CP)."""
    has_contra = _has_contraproducencia_expr()
    con_rows = (
        db.session.query(Actuaciones.contraproducencia, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .group_by(Actuaciones.contraproducencia)
        .order_by(func.count(Actuaciones.id).desc())
        .all()
    )
    sin_cp = max(0, total - sum(int(c) for _, c in con_rows))
    out: list[ContraproducenciaPorTipoItem] = []
    if sin_cp > 0:
        out.append(ContraproducenciaPorTipoItem(valor="Sin contraproducencia", count=sin_cp))
    out.extend(
        ContraproducenciaPorTipoItem(valor=str(v).strip(), count=int(c))
        for v, c in con_rows
    )
    return out


def _actuaciones_por_tipo_operativo(sq) -> list[ActuacionPorTipoOperativoItem]:
    """Agrupa actuaciones filtradas por `Actuaciones.tipo` (valores reales del enum)."""
    rows = (
        db.session.query(Actuaciones.tipo, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .group_by(Actuaciones.tipo)
        .order_by(func.count(Actuaciones.id).desc())
        .all()
    )
    return [
        ActuacionPorTipoOperativoItem(tipo=str(tipo), count=int(cnt))
        for tipo, cnt in rows
    ]


def _ruta_items_ejecucion_por_fecha_ruta(
    desde: date,
    hasta: date,
) -> RutaItemsEjecucionResumen:
    """
    Agrega ítems de ruta por `RutaTrabajo.fecha` (sin turno ni filtros de distrito/inspector).

    Parámetros:
        desde, hasta: rango inclusive sobre fecha de la ruta.

    Retorno:
        Conteos totales y por `estado_ejecucion` (REALIZADO / NO_REALIZADO / sin clasificar).
    """
    rows = (
        db.session.query(RutaItem.estado_ejecucion, func.count(RutaItem.id))
        .join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
        .filter(
            RutaTrabajo.fecha >= desde,
            RutaTrabajo.fecha <= hasta,
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
        )
        .group_by(RutaItem.estado_ejecucion)
        .all()
    )
    realizado = 0
    no_realizado = 0
    sin = 0
    total = 0
    for estado, cnt in rows:
        total += int(cnt)
        if estado is None:
            sin += int(cnt)
        elif estado == "REALIZADO":
            realizado += int(cnt)
        elif estado == "NO_REALIZADO":
            no_realizado += int(cnt)
        else:
            sin += int(cnt)
    return RutaItemsEjecucionResumen(
        total=total,
        estado_ejecucion_realizado=realizado,
        estado_ejecucion_no_realizado=no_realizado,
        estado_ejecucion_sin_clasificar=sin,
    )


def build_indicadores_resumen(
    desde: date,
    hasta: date,
    distrito_id: Optional[int] = None,
    inspector_id: Optional[int] = None,
) -> IndicadoresResumenOut:
    """
    Calcula agregados del dashboard para el periodo y filtros dados.

    Parámetros:
        desde, hasta: fechas inclusive sobre `Actuaciones.fecha`.
        distrito_id, inspector_id: filtros opcionales sobre el conjunto de actuaciones.

    Retorno:
        `IndicadoresResumenOut` listo para serializar JSON.

    Notas:
        ``actas_por_tipo`` y ``actas_labradas_mensual`` excluyen previas/origen (notificación sin
        motivos; comprobación con motivo ``PENDIENTE``).
        ``reinspecciones_realizadas`` usa fecha de cierre de ruta (no fecha de actuación).
        El bloque ``ruta_items_ejecucion`` agrega solo ítems en rutas ``PUBLICADAS``.
    """
    sq = _actuacion_ids_subquery(desde, hasta, distrito_id, inspector_id)
    has_contra = _has_contraproducencia_expr()

    total = db.session.query(func.count()).select_from(sq).scalar() or 0
    total = int(total)

    con_cp = (
        db.session.query(func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .scalar()
        or 0
    )
    con_cp = int(con_cp)
    sin_cp = max(0, total - con_cp)

    top_rows = (
        db.session.query(Actuaciones.contraproducencia, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .filter(has_contra)
        .group_by(Actuaciones.contraproducencia)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(10)
        .all()
    )
    contraproducencias_top = [
        ContraproducenciaTopItem(valor=str(v), count=int(c)) for v, c in top_rows
    ]

    actas_por_tipo = _count_actas_labradas(sq)
    actas_labradas_mensual = _actas_labradas_mensual(sq, desde, hasta)
    ranking_inspectores = _ranking_inspectores(sq)
    reinspecciones_realizadas = _reinspecciones_realizadas(
        desde, hasta, distrito_id, inspector_id
    )
    contraproducencias_por_tipo = _contraproducencias_por_tipo(sq, total)
    actuaciones_por_tipo_operativo = _actuaciones_por_tipo_operativo(sq)

    rubro_rows = (
        db.session.query(Rubro.id, Rubro.nombre, func.count(Actuaciones.id))
        .join(sq, sq.c.id == Actuaciones.id)
        .join(Domicilio, Domicilio.id == Actuaciones.domicilio_id)
        .join(Rubro, Rubro.id == Domicilio.rubro_id)
        .group_by(Rubro.id, Rubro.nombre)
        .order_by(func.count(Actuaciones.id).desc())
        .limit(_TOP_RUBROS_LIMIT)
        .all()
    )
    top_rubros = [
        RubroTopItem(rubro_id=int(rid), nombre=str(nombre), count=int(cnt))
        for rid, nombre, cnt in rubro_rows
    ]

    sum_kg = (
        db.session.query(func.sum(Decomiso.cantidad))
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .scalar()
    )
    total_kg = _float_kg(sum_kg)

    ym_rows = (
        db.session.query(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
            func.sum(Decomiso.cantidad),
        )
        .select_from(Decomiso)
        .join(sq, sq.c.id == Decomiso.actuacion_id)
        .join(Actuaciones, Actuaciones.id == Decomiso.actuacion_id)
        .group_by(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
        )
        .order_by(
            extract("year", Actuaciones.fecha),
            extract("month", Actuaciones.fecha),
        )
        .all()
    )
    por_mes = [
        DecomisoKgPorMesItem(
            anio=int(y),
            mes=int(m),
            kg=_float_kg(kg),
        )
        for y, m, kg in ym_rows
    ]
    decomiso_kg = DecomisoKgResumen(total_kg=total_kg, por_mes=por_mes)

    ruta_part = _ruta_items_ejecucion_por_fecha_ruta(desde, hasta)

    desde_s = desde.isoformat()
    hasta_s = hasta.isoformat()
    n_cola = count_mapa_operativo_pendientes_cola(
        desde=desde_s, hasta=hasta_s, distrito_id=distrito_id, tipo=None
    )
    n_en_ruta = count_mapa_operativo_pendientes_en_ruta(
        desde=desde_s,
        hasta=hasta_s,
        distrito_id=distrito_id,
        tipo=None,
        inspector_id=inspector_id,
    )
    n_real_mapa = count_mapa_operativo_realizados_visita(
        desde=desde_s,
        hasta=hasta_s,
        distrito_id=distrito_id,
        tipo=None,
        inspector_id=inspector_id,
    )
    mapa_op = MapaOperativoResumen(
        pendientes_cola=n_cola,
        pendientes_completar_trabajo=n_en_ruta,
        pendientes_total=n_cola + n_en_ruta,
        realizados_visita=n_real_mapa,
    )

    return IndicadoresResumenOut(
        periodo={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        filtros={
            "distrito_id": distrito_id,
            "inspector_id": inspector_id,
        },
        actuaciones=ActuacionesResumen(
            total=total,
            con_contraproducencia=con_cp,
            sin_contraproducencia=sin_cp,
        ),
        contraproducencias_top=contraproducencias_top,
        actas_por_tipo=actas_por_tipo,
        actas_labradas_mensual=actas_labradas_mensual,
        ranking_inspectores=ranking_inspectores,
        reinspecciones_realizadas=reinspecciones_realizadas,
        contraproducencias_por_tipo=contraproducencias_por_tipo,
        actuaciones_por_tipo_operativo=actuaciones_por_tipo_operativo,
        ruta_items_ejecucion=ruta_part,
        mapa_operativo=mapa_op,
        top_rubros=top_rubros,
        decomiso_kg=decomiso_kg,
    )
