"""
Consulta histórica por DNI/CUIT de un contribuyente (solo lectura).

No modifica contribuyentes, domicilios ni rubros. Agrupa actuaciones y trabajos
pendientes asociados al titular real de cada actuación (domicilio de la actuación),
sin usar ``domicilio.contribuyente_id`` como única fuente para iniciadores compartidos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.domains.establecimientos.utils.documento_normalizer import normalizar_documento
from app.database import db
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    IniciadorRuta,
    Relevamiento,
    RutaItem,
)


@dataclass
class HistorialContribuyenteEntry:
    """Fila interna antes de presentación."""

    act: Actuaciones | None
    ruta_item: RutaItem | None
    iniciador: IniciadorRuta | None
    origen: str
    fecha_efectiva: date


def _documento_sql_expr(column: Any) -> Any:
    """Expresión SQL para comparar documento sin separadores."""
    return func.replace(func.replace(func.replace(column, ".", ""), "-", ""), " ", "")


def contribuyente_ids_por_documento(documento: str) -> list[int]:
    """
    Resuelve ids de contribuyente por documento normalizado.

    Parámetros:
        documento: DNI/CUIT con o sin separadores.

    Retorno:
        Lista de ids (puede estar vacía).
    """
    norm = normalizar_documento(documento)
    if not norm:
        return []
    rows = (
        Contribuyente.query.filter(
            Contribuyente.deleted_at.is_(None),
            _documento_sql_expr(Contribuyente.documento) == norm,
        )
        .with_entities(Contribuyente.id)
        .all()
    )
    return [int(r[0]) for r in rows]


def _actuaciones_query_base(contrib_ids: list[int]):
    """Actuaciones cuyo domicilio operativo de la visita pertenece al contribuyente."""
    return (
        Actuaciones.query.join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(Domicilio.contribuyente_id.in_(contrib_ids))
        .options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.notificacion),
            joinedload(Actuaciones.comprobacion).joinedload(Comprobacion.oficio),
            joinedload(Actuaciones.clausura),
            joinedload(Actuaciones.decomiso),
            joinedload(Actuaciones.inspector),
        )
    )


def _iniciador_ids_para_contrib(contrib_ids: list[int]) -> set[int]:
    """Ids de iniciadores vinculados al contribuyente por cadenas documentales válidas."""
    if not contrib_ids:
        return set()
    ids: set[int] = set()

    rows_act = (
        db.session.query(IniciadorRuta.id)
        .join(Actuaciones, IniciadorRuta.actuacion_id == Actuaciones.id)
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.actuacion_id.isnot(None),
            Domicilio.contribuyente_id.in_(contrib_ids),
        )
        .all()
    )
    ids.update(int(r[0]) for r in rows_act)

    rows_notif = (
        db.session.query(IniciadorRuta.id)
        .join(Actuaciones, Actuaciones.notificacion_id == IniciadorRuta.notificacion_id)
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.notificacion_id.isnot(None),
            Domicilio.contribuyente_id.in_(contrib_ids),
        )
        .all()
    )
    ids.update(int(r[0]) for r in rows_notif)

    rows_comp = (
        db.session.query(IniciadorRuta.id)
        .join(Actuaciones, Actuaciones.comprobacion_id == IniciadorRuta.comprobacion_id)
        .join(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.comprobacion_id.isnot(None),
            Domicilio.contribuyente_id.in_(contrib_ids),
        )
        .all()
    )
    ids.update(int(r[0]) for r in rows_comp)

    rows_dom = (
        db.session.query(IniciadorRuta.id)
        .join(Domicilio, IniciadorRuta.domicilio_id == Domicilio.id)
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            Domicilio.contribuyente_id.in_(contrib_ids),
            IniciadorRuta.tipo_iniciador.in_(("RELEVAMIENTO", "DENUNCIA")),
        )
        .all()
    )
    ids.update(int(r[0]) for r in rows_dom)
    return ids


def _pending_ruta_items(contrib_ids: list[int]) -> list[HistorialContribuyenteEntry]:
    """Ítems de ruta pendientes sin actuación, vinculados al contribuyente por iniciador."""
    ini_ids = _iniciador_ids_para_contrib(contrib_ids)
    if not ini_ids:
        return []

    items = (
        RutaItem.query.filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.is_(None),
            RutaItem.iniciador_ruta_id.in_(ini_ids),
            RutaItem.estado_ruta_item.in_(("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")),
        )
        .options(
            joinedload(RutaItem.iniciador_ruta)
            .joinedload(IniciadorRuta.relevamiento)
            .joinedload(Relevamiento.rubro),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.notificacion),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.oficio),
        )
        .all()
    )
    out: list[HistorialContribuyenteEntry] = []
    for item in items:
        ini = item.iniciador_ruta
        f = _fecha_efectiva(None, item)
        out.append(
            HistorialContribuyenteEntry(
                act=None,
                ruta_item=item,
                iniciador=ini,
                origen="RUTA_ITEM_PENDIENTE",
                fecha_efectiva=f,
            )
        )
    return out


def _fecha_efectiva(act: Actuaciones | None, ruta_item: RutaItem | None) -> date:
    """Fecha para ordenamiento: actuación > cierre > ítem > created_at."""
    if act is not None and act.fecha:
        return act.fecha
    if ruta_item is not None and ruta_item.ejecutado_at:
        return ruta_item.ejecutado_at.date()
    if ruta_item is not None and ruta_item.created_at:
        return ruta_item.created_at.date()
    if act is not None and act.created_at:
        return act.created_at.date() if isinstance(act.created_at, datetime) else act.created_at
    return date.min


def _dedupe_key(entry: HistorialContribuyenteEntry) -> str:
    if entry.act is not None and entry.act.id is not None:
        return f"act:{int(entry.act.id)}"
    if entry.ruta_item is not None and entry.ruta_item.id is not None:
        return f"ri:{int(entry.ruta_item.id)}"
    ini = entry.iniciador
    if ini is not None:
        return f"ini:{ini.id}:{ini.tipo_iniciador}:{entry.fecha_efectiva.isoformat()}"
    return f"unk:{id(entry)}"


def list_historial_por_documento(
    documento: str,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[HistorialContribuyenteEntry], int, str]:
    """
    Historial completo de un contribuyente por DNI/CUIT (solo consulta).

    Parámetros:
        documento: DNI/CUIT (con o sin separadores).
        desde, hasta: filtro opcional sobre fecha efectiva.
        page: página 1-based.
        limit: tamaño de página.

    Retorno:
        Tupla (entries paginadas, total sin paginar, documento_normalizado).

    Errores:
        Ninguno; documento vacío devuelve lista vacía.
    """
    norm = normalizar_documento(documento)
    if not norm:
        return [], 0, norm

    contrib_ids = contribuyente_ids_por_documento(documento)
    if not contrib_ids:
        return [], 0, norm

    q = _actuaciones_query_base(contrib_ids)
    acts = q.all()

    ruta_items_by_act: dict[int, RutaItem] = {}
    if acts:
        act_ids = [int(a.id) for a in acts]
        ri_rows = (
            RutaItem.query.filter(
                RutaItem.actuacion_id.in_(act_ids),
                RutaItem.deleted_at.is_(None),
            )
            .options(
                joinedload(RutaItem.iniciador_ruta)
                .joinedload(IniciadorRuta.relevamiento)
                .joinedload(Relevamiento.rubro),
                joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.notificacion),
            )
            .all()
        )
        for ri in ri_rows:
            if ri.actuacion_id is not None:
                ruta_items_by_act[int(ri.actuacion_id)] = ri

    entries: list[HistorialContribuyenteEntry] = []
    for act in acts:
        ri = ruta_items_by_act.get(int(act.id))
        ini = ri.iniciador_ruta if ri else None
        f = _fecha_efectiva(act, ri)
        entries.append(
            HistorialContribuyenteEntry(
                act=act,
                ruta_item=ri,
                iniciador=ini,
                origen="ACTUACION",
                fecha_efectiva=f,
            )
        )

    entries.extend(_pending_ruta_items(contrib_ids))

    if desde is not None:
        entries = [e for e in entries if e.fecha_efectiva >= desde]
    if hasta is not None:
        entries = [e for e in entries if e.fecha_efectiva <= hasta]

    seen: set[str] = set()
    deduped: list[HistorialContribuyenteEntry] = []
    for e in sorted(entries, key=lambda x: (x.fecha_efectiva, x.act.id if x.act else 0), reverse=True):
        key = _dedupe_key(e)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    total = len(deduped)
    offset = max(0, (page - 1) * limit)
    page_items = deduped[offset : offset + limit]
    return page_items, total, norm
