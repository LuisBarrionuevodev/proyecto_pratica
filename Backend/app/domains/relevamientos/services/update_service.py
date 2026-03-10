from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Relevamiento
from app.utils.fechas import parse_fecha_grid
from app.shared.services.domicilio_repo import get_or_create_domicilio_basico
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_domicilio_if_orphan,
)
from app.domains.relevamientos.services.operational_guard_service import (
    get_iniciador_pendiente_relevamiento,
)


def _get_relevamiento_or_404(relevamiento_id: int) -> Relevamiento:
    rel = (
        Relevamiento.query.filter(
            Relevamiento.id == relevamiento_id,
            Relevamiento.deleted_at.is_(None),
        )
        .limit(1)
        .first()
    )
    if not rel:
        raise ValueError("Relevamiento no encontrado.")
    return rel


def actualizar_relevamiento(relevamiento_id: int, payload: Dict[str, Any]) -> Relevamiento:
    """
    Actualiza un Relevamiento existente en base a un payload canon.

    Args:
        relevamiento_id: id del relevamiento.
        payload: dict canon (sin DB).

    Returns:
        Relevamiento actualizado y commiteado.

    Raises:
        ValueError: si no existe o reglas de negocio.
    """
    rel = _get_relevamiento_or_404(relevamiento_id)
    get_iniciador_pendiente_relevamiento(relevamiento_id)
    old_domicilio_id = rel.domicilio_id

    fecha_raw = payload.get("fecha")
    inspector_nombre = payload.get("inspector_nombre")
    domicilio = payload.get("domicilio") or {}
    calle = domicilio.get("calle")
    numero = domicilio.get("numero")
    rubro_nombre = payload.get("rubro_nombre")
    contraproducencia = payload.get("contraproducencia")

    if not fecha_raw:
        raise ValueError("Fecha obligatoria.")
    if not inspector_nombre:
        raise ValueError("Inspector obligatorio.")
    if not calle or not numero:
        raise ValueError("Calle y número son obligatorios.")

    if bool(rubro_nombre) == bool(contraproducencia):
        raise ValueError("Debe cargar Rubro o Contraproducencia (excluyentes).")

    mes, anio, fecha = parse_fecha_grid(fecha_raw)
    inspector = get_inspectores_o_falla([inspector_nombre])[0]
    rubro = get_rubro_o_falla(rubro_nombre)
    dom = get_or_create_domicilio_basico(calle, numero)
    numero_tipo_override = (payload.get("domicilio") or {}).get("numero_tipo")
    normalizar_domicilio_en_sesion(dom, override_numero_tipo=numero_tipo_override)

    rel.fecha = fecha
    rel.mes = mes
    rel.anio = anio
    rel.inspector_id = inspector.id
    rel.domicilio_id = dom.id
    rel.rubro_id = rubro.id if rubro else None
    rel.contraproducencia = contraproducencia

    db.session.add(rel)
    db.session.commit()

    if old_domicilio_id is not None and old_domicilio_id != rel.domicilio_id:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        db.session.commit()

    # Best-effort geocode (no bloquea la actualización)
    try:
        if rel.domicilio_id:
            on_domicilio_changed(rel.domicilio_id)
    except Exception:
        pass
    return rel
