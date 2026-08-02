"""
Bandejas operativas unificadas para actas de comprobación (oficio / reinspección / recorrido).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import joinedload, selectinload

from app.domains.actuaciones.services.comprobacion_oficio_recorrido_service import (
    iniciador_reinspeccion_por_oficio,
)
from app.domains.actuaciones.services.oficio_editable_service import iniciador_en_ruta_operativa
from app.domains.actuaciones.services.oficio_list_service import list_oficios_by_comprobacion
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import (
    comprobacion_recorrido_resumen_row,
    estado_recorrido_label,
    resultado_cumplimiento_recorrido,
)
from app.domains.actuaciones.services.pendientes_service import (
    _apply_distrito_optional,
    _apply_fecha_comprobacion_acta,
)
from app.domains.establecimientos.services.actuaciones_en_ficha_counts import (
    build_counts_by_eo_from_actuaciones,
)
from app.models import Actuaciones, Domicilio, Expediente, IniciadorRuta, Oficio
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters

def _query_actuaciones_circuito_reinspeccion(filters: ActuacionesPendientesFilters):
    """Actuaciones con envío + oficio + respuesta (sin filtrar por ruta a nivel actuación)."""
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
    q = (
        Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
        .filter(has_envio, has_oficio, has_respuesta)
        .options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            selectinload(Actuaciones.inspector),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.comprobacion),
        )
    )
    q = _apply_fecha_comprobacion_acta(q, filters)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    return q.order_by(Actuaciones.id.desc())


def _iniciador_reinspeccion_por_oficio(oficio_id: int) -> IniciadorRuta | None:
    return iniciador_reinspeccion_por_oficio(oficio_id)


def _iniciador_reinspeccion_legacy_actuacion(actuacion_id: int) -> IniciadorRuta | None:
    """Iniciador REINSPECCION_OFICIO sin ``oficio_id`` (datos legados / tests)."""
    return (
        IniciadorRuta.query.filter_by(actuacion_id=int(actuacion_id))
        .filter(IniciadorRuta.oficio_id.is_(None))
        .filter(IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO")
        .filter(IniciadorRuta.deleted_at.is_(None))
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _iniciador_para_oficio_en_actuacion(oficio: Oficio, act: Actuaciones) -> IniciadorRuta | None:
    ini = _iniciador_reinspeccion_por_oficio(oficio.id)
    if ini is not None:
        return ini
    oficios = list_oficios_by_comprobacion(int(act.comprobacion_id))
    if len(oficios) == 1 and oficios[0].id == oficio.id:
        return _iniciador_reinspeccion_legacy_actuacion(act.id)
    return None


def _expediente_respuesta_por_oficio(oficio_id: int) -> Expediente | None:
    return (
        Expediente.query.filter_by(oficio_id=int(oficio_id))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def _tramite_reinspeccion_oficio_cumplido(ini: IniciadorRuta | None) -> bool:
    """
    True si el trámite de reinspección por oficio ya cerró operativamente.

    Reencolados por contraproducencia quedan en ``PENDIENTE`` y siguen listables.
    """
    if ini is None:
        return False
    if ini.estado_iniciador == "CUMPLIDO":
        return True
    return ini.estado_iniciador in inactive_estados()


def list_pendientes_reinspeccion_oficio_filas(
    filters: ActuacionesPendientesFilters,
) -> List[Tuple[Actuaciones, Oficio, Optional[IniciadorRuta]]]:
    """
    Filas pendientes de reinspección **por oficio/iniciador** (PR4b).

    Una actuación con dos oficios puede generar dos filas si ninguno (o solo uno) está en ruta activa.
    """
    acts = _query_actuaciones_circuito_reinspeccion(filters).all()
    filas: List[Tuple[Actuaciones, Oficio, Optional[IniciadorRuta]]] = []
    for act in acts:
        if act.comprobacion_id is None:
            continue
        for ofi in list_oficios_by_comprobacion(int(act.comprobacion_id)):
            if _expediente_respuesta_por_oficio(ofi.id) is None:
                continue
            ini = _iniciador_para_oficio_en_actuacion(ofi, act)
            if iniciador_en_ruta_operativa(ini):
                continue
            if _tramite_reinspeccion_oficio_cumplido(ini):
                continue
            filas.append((act, ofi, ini))
    return filas


def list_pendientes_reinspeccion_oficio(
    filters: ActuacionesPendientesFilters,
) -> List[Actuaciones]:
    """
    Reinspecciones por oficio **pendientes de planificación en ruta** (F3.6b).

    Documental:

    - Expediente de envío de acta activo (``oficio_id`` NULL, no borrado).
    - Oficio administrativo activo (no borrado).
    - Expediente de respuesta al oficio activo (``oficio_id`` al oficio de la misma comprobación;
      ``tipo_expediente`` ``RESPUESTA_OFICIO`` o ``NULL`` legado).

    Puede existir o no ``IniciadorRuta`` tipo ``REINSPECCION_OFICIO``; eso **no** oculta la fila.

    Fuera de bandeja solo si existe un ``RutaItem`` **incorporado** a planificación operativa:

    - ``IniciadorRuta`` mismo ``actuacion_id``, tipo ``REINSPECCION_OFICIO``, no soft-deleted.
    - ``RutaItem`` no soft-deleted.
    - ``RutaTrabajo.estado_ruta`` en ``PUBLICADA`` | ``EN_CURSO`` (STAB-3: ``BORRADOR`` no oculta).

    Si la ruta está ``BORRADOR`` / ``CERRADA`` / ``CANCELADA``, el ítem está borrado en soft delete, o el iniciador no
    tiene ítem en esa ruta, la actuación **sigue** en bandeja (puede tener o no iniciador materializado).

    Fechas / distrito: ``Actuaciones.fecha`` vía ``_apply_fecha`` / ``_apply_distrito_optional``.

    Compat: devuelve actuaciones únicas presentes en ``list_pendientes_reinspeccion_oficio_filas``.
    """
    seen: set[int] = set()
    out: List[Actuaciones] = []
    for act, _ofi, _ini in list_pendientes_reinspeccion_oficio_filas(filters):
        if act.id not in seen:
            seen.add(act.id)
            out.append(act)
    return out


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
    Filtros de texto opcionales (subcadena, case-insensitive) sobre ``comprobacion_recorrido_resumen_row``.
    ``tipo_final`` usa ``resultado_cumplimiento_recorrido`` (incluye segunda visita si aplica).
    Mes/año explícitos filtran ``Comprobacion.mes/anio``; rango filtra ``Actuaciones.fecha``.
    """
    q = Actuaciones.query.filter(Actuaciones.comprobacion_id.isnot(None))
    q = _apply_fecha_comprobacion_acta(q, filters)
    distrito_id = getattr(filters, "distrito_id", None)
    q = _apply_distrito_optional(q, distrito_id)
    rows: List[Actuaciones] = q.order_by(Actuaciones.id.desc()).limit(limit).all()

    counts_by_eo = build_counts_by_eo_from_actuaciones(rows)

    def _digits_only(value: str) -> str:
        return "".join(c for c in value if c.isdigit())

    def _expediente_search_blob(act: Actuaciones, row: dict) -> str:
        parts: list[str] = []
        for item in row.get("oficios_resumen") or []:
            if not isinstance(item, dict):
                continue
            parts.extend(
                [
                    str(item.get("expediente_texto") or ""),
                    str(item.get("numero_expediente") or ""),
                    str(item.get("anio_expediente") or ""),
                    f"{item.get('numero_expediente') or ''}/{item.get('anio_expediente') or ''}",
                    f"{item.get('numero_expediente') or ''}{item.get('anio_expediente') or ''}",
                ]
            )
        parts.extend(
            [
                f"{row.get('expediente_numero') or ''}",
                f"{row.get('expediente_anio') or ''}",
                f"{row.get('expediente_numero') or ''}/{row.get('expediente_anio') or ''}",
                f"{row.get('expediente_respuesta_numero') or ''}",
                f"{row.get('expediente_respuesta_anio') or ''}",
                f"{row.get('expediente_respuesta_numero') or ''}/{row.get('expediente_respuesta_anio') or ''}",
            ]
        )
        cid = act.comprobacion_id
        if cid:
            exps = (
                Expediente.query.filter_by(comprobacion_id=int(cid))
                .filter(Expediente.deleted_at.is_(None))
                .all()
            )
            for exp in exps:
                num = getattr(exp, "numero_expediente", "") or ""
                an = getattr(exp, "anio", "") or ""
                parts.extend([str(num), str(an), f"{num}/{an}", f"{num}{an}"])
        return " ".join(p for p in parts if p).lower()

    def _expediente_matches_query(act: Actuaciones, row: dict, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        blob = _expediente_search_blob(act, row)
        if q in blob:
            return True
        if q.replace("/", "") in blob.replace("/", ""):
            return True
        q_digits = _digits_only(q)
        if not q_digits:
            return False
        if q_digits in _digits_only(blob):
            return True
        q_norm = q_digits.lstrip("0") or q_digits
        for item in row.get("oficios_resumen") or []:
            if not isinstance(item, dict):
                continue
            exp_num = _digits_only(str(item.get("numero_expediente") or ""))
            if not exp_num:
                continue
            if q_digits in exp_num or q_norm in exp_num.lstrip("0"):
                return True
        for exp in (
            Expediente.query.filter_by(comprobacion_id=int(act.comprobacion_id))
            .filter(Expediente.deleted_at.is_(None))
            .all()
            if act.comprobacion_id
            else []
        ):
            exp_num = _digits_only(str(getattr(exp, "numero_expediente", "") or ""))
            if exp_num and (q_digits in exp_num or q_norm in exp_num.lstrip("0")):
                return True
        return False

    def _oficio_search_blob(row: dict) -> str:
        parts: list[str] = []
        if row.get("oficios_texto"):
            parts.append(str(row["oficios_texto"]))
        for item in row.get("oficios_resumen") or []:
            if isinstance(item, dict):
                parts.append(str(item.get("oficio_texto") or ""))
                parts.append(
                    f"{item.get('numero_oficio') or item.get('numero') or ''}"
                    f"{item.get('anio_oficio') or item.get('anio') or ''}"
                )
        parts.append(f"{row.get('oficio_numero') or ''}{row.get('oficio_anio') or ''}")
        return " ".join(parts).lower()

    def _keep(act: Actuaciones) -> bool:
        row = comprobacion_recorrido_resumen_row(act, counts_by_eo=counts_by_eo)
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
            if not _expediente_matches_query(act, row, expediente_numero):
                return False
        if oficio_numero and oficio_numero.strip():
            if oficio_numero.strip().lower() not in _oficio_search_blob(row):
                return False
        if estado_recorrido and estado_recorrido.strip():
            if estado_recorrido_label(act).lower() != estado_recorrido.strip().lower():
                return False
        if tipo_final and tipo_final.strip():
            rc = (resultado_cumplimiento_recorrido(act) or "").strip().upper()
            if rc != tipo_final.strip().upper():
                return False
        return True

    return [a for a in rows if _keep(a)]
