from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Actuaciones
from app.utils.fechas import parse_fecha_grid

from .previas_service import resolver_previas
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.domains.actuaciones.attach.notificacion import attach_notificacion
from app.domains.actuaciones.attach.comprobacion import attach_comprobacion
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.attach.oficio import attach_oficio
from app.domains.actuaciones.attach.expediente import attach_expediente
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)


def crear_actuacion_desde_payload(payload: Dict[str, Any]) -> Actuaciones:
    """
    Crea una `Actuaciones` y adjunta entidades relacionadas según el payload canon.

    Este service mantiene el comportamiento histórico:
    - Determina `mes/anio/fecha` desde `fecha_actuacion`.
    - Crea/obtiene OT y aplica la regla "1 actuación por OT".
    - Resuelve catálogos (rubro/inspectores) y dominios (contribuyente/domicilio).
    - Resuelve previas (notificación/comprobación) y adjunta actas del día.
    - Adjunta oficio/expediente si vienen en payload.
    - Persiste con `db.session.commit()` al final.

    Args:
        payload: dict canon del mapper (sin DB).

    Returns:
        Instancia de `Actuaciones` creada y commiteada.

    Raises:
        ValueError: si se violan reglas de negocio (p.ej. OT duplicada, catálogos inexistentes, validaciones de actas).
    """
    fecha_str = payload.get("fecha_actuacion")
    mes, anio, fecha = parse_fecha_grid(fecha_str)

    # OT
    ot = get_or_create_orden_trabajo(payload.get("orden_trabajo_numero"), fecha_str)

    # Regla: 1 actuación por OT
    existente = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
    if existente:
        raise ValueError("Ya existe una actuación asociada a esa Orden de Trabajo.")

    act = Actuaciones(
        fecha=fecha,
        mes=mes,
        anio=anio,
        tipo=payload.get("tipo_actuacion"),
        contraproducencia=payload.get("contraproducencia"),
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()  # necesitamos act.id para attach_* que dependen de actuacion_id

    # Catálogos / entidades base
    # Si no hay tipo y hay contraproducencia, permitimos domicilio sin rubro/contribuyente
    allow_missing_catalogs = payload.get("tipo_actuacion") is None and payload.get("contraproducencia") is not None
    rubro = get_rubro_o_falla(payload.get("rubro_nombre"))
    contrib = resolve_contribuyente(payload.get("contribuyente"))
    dom = get_or_create_domicilio(
        payload.get("domicilio"),
        contrib,
        rubro,
        allow_missing_catalogs=allow_missing_catalogs,
    )
    if dom:
        act.domicilio_id = dom.id
        numero_tipo_override = (payload.get("domicilio") or {}).get("numero_tipo")
        normalizar_domicilio_en_sesion(dom, override_numero_tipo=numero_tipo_override)

    # Inspectores (catálogo)
    nombres = payload.get("inspectores") or []
    if nombres:
        act.inspector = get_inspectores_o_falla(nombres)

    # Previas (si aplica)
    resolver_previas(act, payload)

    # Actas (si vienen)
    attach_inspeccion(act, payload.get("acta_inspeccion_num"), crear=True)
    attach_notificacion(act, payload.get("notificacion"))
    attach_comprobacion(act, payload.get("comprobacion"))
    attach_clausura(act, payload.get("clausura"), crear=True)
    attach_decomiso(act, payload.get("decomiso"), crear=True)

    # Oficio / Expediente
    oficio = attach_oficio(payload.get("oficio"), act.comprobacion_id)
    expediente = attach_expediente(payload.get("expediente"), act.comprobacion_id, oficio.id if oficio else None)

    # si tu Actuaciones tiene relación/columna expediente_id, acá se asigna
    if expediente and hasattr(act, "expediente_id"):
        act.expediente_id = expediente.id

    db.session.add(act)
    db.session.commit()
    return act
