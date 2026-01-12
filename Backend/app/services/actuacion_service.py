from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Actuaciones
from app.utils.fechas import parse_fecha_grid

from app.services.actuaciones.previas_service import resolver_previas
from app.services.actuaciones.attach.inspeccion import attach_inspeccion
from app.services.actuaciones.attach.clausura import attach_clausura
from app.services.actuaciones.attach.decomiso import attach_decomiso
from app.services.actuaciones.attach.notificacion import attach_notificacion
from app.services.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.services.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.services.actuaciones.domains.contribuyente import resolve_contribuyente
from app.services.actuaciones.domains.domicilio import get_or_create_domicilio
from app.services.actuaciones.domains.orden_trabajo import get_or_create_orden_trabajo
from app.services.actuacion_helpers import (
    attach_comprobacion,
    attach_oficio,
    attach_expediente,
)


def _get_actuacion_or_404(actuacion_id: int) -> Actuaciones:
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise ValueError("Actuación no encontrada.")
    return act



def crear_actuacion_desde_payload(payload: Dict[str, Any]) -> Actuaciones:
    """
    Crea Actuación + adjunta entidades según payload.
    Espera payload canon (del mapper).
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
    rubro = get_rubro_o_falla(payload.get("rubro_nombre"))
    contrib = resolve_contribuyente(payload.get("contribuyente"))
    dom = get_or_create_domicilio(payload.get("domicilio"), contrib, rubro)
    if dom:
        act.domicilio_id = dom.id

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


def actualizar_actuacion(actuacion_id: int, payload: Dict[str, Any]) -> Actuaciones:
    """
    Update “por payload canon”.
    """
    act = _get_actuacion_or_404(actuacion_id)

    # Fecha
    if payload.get("fecha_actuacion"):
        mes, anio, fecha = parse_fecha_grid(payload["fecha_actuacion"])
        act.fecha = fecha
        act.mes = mes
        act.anio = anio

    # Tipo / contraproducencia
    if "tipo_actuacion" in payload:
        act.tipo = payload.get("tipo_actuacion")
    if "contraproducencia" in payload:
        act.contraproducencia = payload.get("contraproducencia")

    # OT (si permitís cambiarla)
    if payload.get("orden_trabajo_numero") and payload.get("fecha_actuacion"):
        ot = get_or_create_orden_trabajo(payload.get("orden_trabajo_numero"), payload.get("fecha_actuacion"))

        # Regla 1 actuación por OT (si cambia)
        if ot.id != act.orden_trabajo_id:
            existente = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
            if existente:
                raise ValueError("Ya existe una actuación asociada a esa Orden de Trabajo.")
            act.orden_trabajo_id = ot.id

    # Catálogos y domicilio
    rubro = get_rubro_o_falla(payload.get("rubro_nombre")) if "rubro_nombre" in payload else None
    contrib = resolve_contribuyente(payload.get("contribuyente")) if "contribuyente" in payload else None
    if "domicilio" in payload:
        # si mandan domicilio, exige que rubro/contrib estén presentes o ya existan
        if rubro is None:
            rubro = get_rubro_o_falla(payload.get("rubro_nombre"))
        if contrib is None:
            contrib = resolve_contribuyente(payload.get("contribuyente"))

        dom = get_or_create_domicilio(payload.get("domicilio"), contrib, rubro)
        act.domicilio_id = dom.id if dom else None

    # Inspectores
    if "inspectores" in payload:
        nombres = payload.get("inspectores") or []
        act.inspector = get_inspectores_o_falla(nombres) if nombres else []

    # Previas
    resolver_previas(act, payload)

    # Actas (update)
    if "acta_inspeccion_num" in payload:
        attach_inspeccion(act, payload.get("acta_inspeccion_num"), crear=False)

    if "notificacion" in payload:
        attach_notificacion(act, payload.get("notificacion"))

    if "comprobacion" in payload:
        attach_comprobacion(act, payload.get("comprobacion"))

    if "clausura" in payload:
        attach_clausura(act, payload.get("clausura"), crear=False)

    if "decomiso" in payload:
        attach_decomiso(act, payload.get("decomiso"), crear=False)

    # Oficio / Expediente
    oficio = attach_oficio(payload.get("oficio"),act.comprobacion_id  if "oficio" in payload else None)
    expediente = attach_expediente(payload.get("expediente"), act.comprobacion_id, oficio.id if oficio else None) if "expediente" in payload else None
    if expediente and hasattr(act, "expediente_id"):
        act.expediente_id = expediente.id

    db.session.add(act)
    db.session.commit()
    return act


def eliminar_actuacion(actuacion_id: int) -> None:
    act = _get_actuacion_or_404(actuacion_id)
    db.session.delete(act)
    db.session.commit()
