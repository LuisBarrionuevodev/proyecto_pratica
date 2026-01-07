from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Notificacion, Comprobacion

from app.services.actuacion_helpers import (
    parse_fecha_grid,
    acta_6,
    get_rubro_o_falla,
    get_inspectores_o_falla,
    resolve_contribuyente,
    get_or_create_domicilio,
    get_or_create_orden_trabajo,
    attach_inspeccion,
    attach_notificacion,
    attach_comprobacion,
    attach_clausura,
    attach_decomiso,
    attach_oficio,
    attach_expediente,
)


def _get_actuacion_or_404(actuacion_id: int) -> Actuaciones:
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise ValueError("Actuación no encontrada.")
    return act


def _resolver_previas(act, payload: Dict[str, Any]) -> None:
    anio = act.anio
    mes = act.mes

    # NOTIFICACION PREVIA (mínima, sin motivos)
    prev_noti_num = acta_6(payload.get("notificacion_previa_num") or payload.get("acta_notificacion_previa_num"))
    if prev_noti_num:
        noti = Notificacion.query.filter_by(numero_acta=prev_noti_num, anio=anio).first()
        if not noti:
            noti = Notificacion(numero_acta=prev_noti_num, anio=anio, mes=mes)
            db.session.add(noti)
            db.session.flush()
        act.notificacion_id = noti.id

    # COMPROBACION PREVIA (mínima; motivo opcional)
    prev_comp_num = acta_6(payload.get("comprobacion_previa_num") or payload.get("acta_comprobacion_previa_num"))
    if prev_comp_num:
        comp = Comprobacion.query.filter_by(numero_acta=prev_comp_num, anio=anio).first()

        # Si querés permitir mandar un motivo para la previa (opcional):
        motivo_prev = (payload.get("comprobacion_previa_motivo") or "").strip()

        if not comp:
            # ⚠️ si motivo es NOT NULL en DB, usá un placeholder explícito
            # mejor "PENDIENTE" o "SIN_DATO" que "default"
            motivo_inicial = motivo_prev if motivo_prev else "PENDIENTE"
            comp = Comprobacion(numero_acta=prev_comp_num, anio=anio, mes=mes, motivo=motivo_inicial)
            db.session.add(comp)
            db.session.flush()
        else:
            # si existe y me pasaron motivo_prev, actualizo; si no, no toco
            if motivo_prev:
                comp.motivo = motivo_prev
                comp.mes = mes
                db.session.add(comp)

        act.comprobacion_id = comp.id

    """
    Previas (modo upsert):
    - Si viene previa y NO existe en DB, se CREA con numero_acta+anio+mes.
    - NO exige motivos (ni en notificación ni en comprobación).
    - Se asocia a la actuación (act.notificacion_id / act.comprobacion_id).

    Importante: acá NO tocamos la lógica de "acta del día" (attach_notificacion/attach_comprobacion),
    esto solo resuelve las *previas* cuando el usuario carga un número de referencia.
    """
    anio = act.anio
    mes = act.mes

    # -------------------------
    # NOTIFICACION PREVIA
    # -------------------------
    prev_noti_num = acta_6(payload.get("notificacion_previa_num") or payload.get("acta_notificacion_previa_num"))
    if prev_noti_num:
        noti = Notificacion.query.filter_by(numero_acta=prev_noti_num, anio=anio).first()
        if not noti:
            # crear previa mínima (sin motivos)
            noti = Notificacion(numero_acta=prev_noti_num, anio=anio, mes=mes)
            db.session.add(noti)
            db.session.flush()
        act.notificacion_id = noti.id

    # -------------------------
    # COMPROBACION PREVIA
    # -------------------------
    prev_comp_num = acta_6(payload.get("comprobacion_previa_num") or payload.get("acta_comprobacion_previa_num"))
    if prev_comp_num:
        comp = Comprobacion.query.filter_by(numero_acta=prev_comp_num, anio=anio).first()
        if not comp:
            # crear previa mínima (sin motivo)
            # ⚠️ si tu modelo Comprobacion tiene campos NOT NULL extra, agregalos acá con defaults
            comp = Comprobacion(numero_acta=prev_comp_num, anio=anio, mes=mes, motivo= "default")
            db.session.add(comp)
            db.session.flush()
        act.comprobacion_id = comp.id



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
    _resolver_previas(act, payload)

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
    _resolver_previas(act, payload)

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
    oficio = attach_oficio(payload.get("oficio")) if "oficio" in payload else None
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
