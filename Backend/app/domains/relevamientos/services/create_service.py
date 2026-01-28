from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Relevamiento
from app.utils.fechas import parse_fecha_grid
from app.shared.services.domicilio_repo import get_or_create_domicilio_basico
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla


def crear_relevamiento_desde_payload(payload: Dict[str, Any]) -> Relevamiento:
    """
    Crea un Relevamiento desde un payload canon.

    Args:
        payload: dict canon (sin DB) con fecha, inspector, domicilio y rubro/contraproducencia.

    Returns:
        Relevamiento creado y commiteado.

    Raises:
        ValueError: si faltan campos obligatorios o reglas de negocio.
    """
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

    rel = Relevamiento(
        fecha=fecha,
        mes=mes,
        anio=anio,
        inspector_id=inspector.id,
        domicilio_id=dom.id,
        rubro_id=rubro.id if rubro else None,
        contraproducencia=contraproducencia,
    )
    db.session.add(rel)
    db.session.commit()
    return rel
