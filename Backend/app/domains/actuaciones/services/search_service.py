"""
Búsqueda liviana de actuaciones y órdenes de trabajo (STAB-6).

No devuelve payload de grilla completo; solo sugerencias para Autocomplete.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.database import db
from app.models import (
    Actuaciones,
    Comprobacion,
    Contribuyente,
    Domicilio,
    Inspeccion,
    Notificacion,
    OrdenTrabajo,
    Rubro,
)
from app.utils.actas import acta_6


def _contrib_label(c: Contribuyente | None) -> str | None:
    if c is None:
        return None
    ap = (c.apellido or "").strip()
    no = (c.nombre or "").strip()
    if ap or no:
        return f"{ap} {no}".strip()
    doc = (c.documento or "").strip()
    return doc or None


def _domicilio_linea(dom: Domicilio | None) -> str | None:
    if dom is None:
        return None
    calle = (dom.calle or "").strip()
    num = (dom.numero or "").strip()
    if calle and num:
        return f"{calle} {num}"
    return calle or num or None


def _build_label(
    *,
    ot_num: str | None,
    fecha_iso: str | None,
    dom_linea: str | None,
    rubro: str | None,
    contrib: str | None,
) -> str:
    parts: list[str] = []
    if ot_num:
        parts.append(f"OT {ot_num}")
    if fecha_iso:
        parts.append(fecha_iso)
    if dom_linea:
        parts.append(dom_linea)
    elif contrib:
        parts.append(contrib)
    if rubro:
        parts.append(rubro)
    return " · ".join(parts) if parts else "Actuación"


def buscar_actuaciones_liviano(q: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """
    Busca actuaciones por OT, domicilio, contribuyente, rubro o número de acta.

    Parámetros:
        q: texto de búsqueda (mín. 2 caracteres).
        limit: máximo de filas.

    Retorno:
        Lista de dicts livianos con `id`, `label` y campos de contexto.
    """
    term = (q or "").strip()
    if len(term) < 2:
        raise ValueError("Ingresá al menos 2 caracteres para buscar.")

    like = f"%{term}%"
    ot_norm = acta_6(term) if term.replace(" ", "").isdigit() else None
    acta_norm = acta_6(term) if term.replace(" ", "").isdigit() else None

    query = (
        Actuaciones.query.options(
            joinedload(Actuaciones.orden_trabajo),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(Actuaciones.inspeccion),
            joinedload(Actuaciones.notificacion),
            joinedload(Actuaciones.comprobacion),
        )
        .outerjoin(OrdenTrabajo, Actuaciones.orden_trabajo_id == OrdenTrabajo.id)
        .outerjoin(Domicilio, Actuaciones.domicilio_id == Domicilio.id)
        .outerjoin(Contribuyente, Domicilio.contribuyente_id == Contribuyente.id)
        .outerjoin(Rubro, Domicilio.rubro_id == Rubro.id)
        .outerjoin(Inspeccion, Inspeccion.actuacion_id == Actuaciones.id)
        .outerjoin(Notificacion, Actuaciones.notificacion_id == Notificacion.id)
        .outerjoin(Comprobacion, Actuaciones.comprobacion_id == Comprobacion.id)
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
    ]
    if ot_norm:
        conds.append(OrdenTrabajo.numero_acta == ot_norm)
    if acta_norm:
        conds.extend(
            [
                Inspeccion.numero_acta == acta_norm,
                Notificacion.numero_acta == acta_norm,
                Comprobacion.numero_acta == acta_norm,
            ]
        )

    rows = (
        query.filter(or_(*conds))
        .order_by(Actuaciones.id.desc())
        .limit(int(limit))
        .all()
    )

    out: list[dict[str, Any]] = []
    for act in rows:
        ot = act.orden_trabajo
        dom = act.domicilio
        rub = dom.rubro if dom else None
        fecha_iso = act.fecha.isoformat() if act.fecha else None
        ot_num = ot.numero_acta if ot else None
        dom_linea = _domicilio_linea(dom)
        contrib = _contrib_label(dom.contribuyente if dom else None)
        label = _build_label(
            ot_num=ot_num,
            fecha_iso=fecha_iso,
            dom_linea=dom_linea,
            rubro=(rub.nombre if rub else None),
            contrib=contrib,
        )
        out.append(
            {
                "id": int(act.id),
                "label": label,
                "orden_trabajo_numero": ot_num,
                "fecha_actuacion": fecha_iso,
                "tipo_actuacion": act.tipo,
                "domicilio_texto": dom_linea,
                "rubro_nombre": rub.nombre if rub else None,
                "contribuyente_texto": contrib,
            }
        )
    return out


def buscar_ordenes_liviano(q: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """
    Busca órdenes de trabajo por número (parcial o exacto normalizado).

    Parámetros:
        q: número o fragmento.
        limit: máximo de filas.

    Retorno:
        Lista con `id`, `numero_acta`, `anio`, `label`, `tiene_actuacion`.
    """
    term = (q or "").strip()
    if not term:
        raise ValueError("Ingresá un número de orden para buscar.")

    like = f"%{term}%"
    ot_norm = acta_6(term) if term.replace(" ", "").isdigit() else None

    conds = [OrdenTrabajo.numero_acta.ilike(like)]
    if ot_norm:
        conds.append(OrdenTrabajo.numero_acta == ot_norm)

    ots = (
        OrdenTrabajo.query.filter(OrdenTrabajo.deleted_at.is_(None))
        .filter(or_(*conds))
        .order_by(OrdenTrabajo.id.desc())
        .limit(int(limit))
        .all()
    )

    ot_ids = [o.id for o in ots]
    actuadas: set[int] = set()
    if ot_ids:
        actuadas = {
            int(r[0])
            for r in db.session.query(Actuaciones.orden_trabajo_id)
            .filter(Actuaciones.orden_trabajo_id.in_(ot_ids))
            .all()
        }

    out: list[dict[str, Any]] = []
    for ot in ots:
        num = ot.numero_acta
        anio = ot.anio
        label = f"OT {num}" + (f" / {anio}" if anio else "")
        out.append(
            {
                "id": int(ot.id),
                "numero_acta": num,
                "anio": anio,
                "label": label,
                "tiene_actuacion": int(ot.id) in actuadas,
            }
        )
    return out
