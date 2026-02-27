from __future__ import annotations

from datetime import date, datetime

from app.database import db
from app.models import Actuaciones, Domicilio, Inspector, Relevamiento
from app.models.actuaciones_inspector import actuaciones_inspector


def _serialize_dt(value: date | datetime | None) -> str | None:
    """Serializa fechas/datetimes a ISO string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def _build_domicilio_label(domicilio: Domicilio | None) -> str:
    """
    Arma nomenclatura de domicilio para popup.

    Reglas:
      - Si hay esquina_normalizada => "{calle} y {esquina}".
      - Si no hay esquina => "{calle} {numero}".
      - Fallback de calle: calle_normalizada -> calle_raw -> calle.
      - Si no hay número, retorna solo calle.
    """
    if domicilio is None:
        return "-"

    calle = (
        (domicilio.calle_normalizada or "").strip()
        or (domicilio.calle_raw or "").strip()
        or (domicilio.calle or "").strip()
    )
    if not calle:
        calle = "-"

    esquina = (domicilio.esquina_normalizada or "").strip()
    numero = (domicilio.numero or "").strip()

    if esquina:
        return f"{calle} y {esquina}"
    if numero:
        return f"{calle} {numero}"
    return calle


def _get_actuacion_inspectores(actuacion_id: int) -> list[str]:
    """Obtiene inspectores vinculados a una actuación."""
    rows = (
        db.session.query(Inspector.nombre)
        .join(actuaciones_inspector, Inspector.id == actuaciones_inspector.c.inspector_id)
        .filter(actuaciones_inspector.c.actuaciones_id == actuacion_id)
        .filter(actuaciones_inspector.c.deleted_at.is_(None))
        .all()
    )
    return [name for (name,) in rows if name]


def _resolve_actuacion(ref_id: int) -> Actuaciones | None:
    """
    Resuelve actuación por id.

    Fallback:
      - Si no existe actuación con ese id, interpreta ref_id como domicilio_id
        y devuelve la actuación más reciente de ese domicilio.
    """
    by_id = Actuaciones.query.get(ref_id)
    if by_id:
        return by_id

    return (
        Actuaciones.query.filter_by(domicilio_id=ref_id)
        .order_by(
            Actuaciones.fecha.desc(),
            Actuaciones.created_at.desc(),
            Actuaciones.id.desc(),
        )
        .first()
    )


def _resolve_relevamiento(ref_id: int) -> Relevamiento | None:
    """
    Resuelve relevamiento por id.

    Fallback:
      - Si no existe relevamiento con ese id, interpreta ref_id como domicilio_id
        y devuelve el relevamiento más reciente de ese domicilio.
    """
    by_id = Relevamiento.query.get(ref_id)
    if by_id:
        return by_id

    return (
        Relevamiento.query.filter_by(domicilio_id=ref_id)
        .order_by(
            Relevamiento.fecha.desc(),
            Relevamiento.created_at.desc(),
            Relevamiento.id.desc(),
        )
        .first()
    )


def get_popup_detail(kind: str, ref_id: int) -> dict:
    """
    Devuelve detalle de popup para mapa.

    Args:
        kind: "actuacion" o "relevamiento".
        ref_id: id de entidad. También admite domicilio_id como fallback.

    Returns:
        Payload unificado para popup.

    Raises:
        ValueError: si kind es inválido o no se encuentra la entidad.
    """
    if kind not in {"actuacion", "relevamiento"}:
        raise ValueError("Kind inválido. Debe ser 'actuacion' o 'relevamiento'.")

    if kind == "actuacion":
        act = _resolve_actuacion(ref_id)
        if not act:
            raise ValueError("Actuación no encontrada.")

        inspeccion = act.inspeccion
        acta_inspeccion = None
        if inspeccion and inspeccion.numero_acta and inspeccion.anio:
            acta_inspeccion = f"{inspeccion.numero_acta}/{inspeccion.anio}"

        return {
            "kind": "actuacion",
            "title": "Actuación",
            "fecha": _serialize_dt(act.fecha),
            "created_at": _serialize_dt(act.created_at),
            "domicilio": _build_domicilio_label(act.domicilio),
            "inspectores": _get_actuacion_inspectores(act.id),
            "acta_inspeccion": acta_inspeccion,
            "tipo": act.tipo,
        }

    rel = _resolve_relevamiento(ref_id)
    if not rel:
        raise ValueError("Relevamiento no encontrado.")

    inspectores = [rel.inspector.nombre] if rel.inspector and rel.inspector.nombre else []
    return {
        "kind": "relevamiento",
        "title": "Relevamiento",
        "fecha": _serialize_dt(rel.fecha),
        "created_at": _serialize_dt(rel.created_at),
        "domicilio": _build_domicilio_label(rel.domicilio),
        "inspectores": inspectores,
        "acta_inspeccion": None,
        "tipo": None,
    }
