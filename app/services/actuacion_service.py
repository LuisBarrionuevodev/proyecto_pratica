from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones

from app.services.actuacion_helpers import (
    parse_fecha_grid,
    get_or_create_orden_trabajo,
    get_or_create_rubro,
    resolve_contribuyente,
    get_or_create_domicilio,
    get_inspectores_o_falla,
    attach_inspeccion,
    attach_notificacion,
    attach_comprobacion,
    attach_clausura,
    attach_decomiso,
    attach_oficio,
    attach_expediente,
)


# =========================================================
# Service CREATE
# =========================================================

def crear_actuacion_desde_payload(payload: Dict[str, Any]) -> Actuaciones:
    """
    Crea una actuación desde el payload del mapper.

    Regla madre:
    - 1 actuación por Orden de Trabajo.
    - Si la OT ya tiene actuación -> rechazo duro.
    """

    fecha_str = payload["fecha_actuacion"]
    mes, anio, fecha_date = parse_fecha_grid(fecha_str)

    # 1) OT
    ot = get_or_create_orden_trabajo(payload["orden_trabajo_numero"], fecha_str)
    db.session.flush()

    # 2) Verificar si ya existe actuación para esa OT
    existente = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
    if existente:
        raise ValueError("Ya existe una actuación para esa Orden de Trabajo.")

    # 3) Crear actuación base
    actuacion = Actuaciones(
        fecha=fecha_date,
        mes=mes,
        anio=anio,
        orden_trabajo_id=ot.id,
    )

    # Campos simples
    if payload.get("tipo_actuacion") is not None:
        actuacion.tipo = payload["tipo_actuacion"]

    if payload.get("contraproducencia") is not None:
        actuacion.contraproducencia = payload["contraproducencia"]

    db.session.add(actuacion)
    db.session.flush()

    # 4) Resolver rubro + contribuyente + domicilio
    rubro = get_or_create_rubro(payload.get("rubro_nombre"))
    contrib = resolve_contribuyente(payload.get("contribuyente"))
    db.session.flush()

    domicilio = get_or_create_domicilio(payload.get("domicilio"), contrib, rubro)
    db.session.flush()

    if domicilio:
        actuacion.domicilio_id = domicilio.id

    # 5) Inspectores (catálogo)
    nombres = payload.get("inspectores") or []
    if nombres:
        actuacion.inspector = get_inspectores_o_falla(nombres)

    # 6) Actas principales y secundarias
    attach_inspeccion(actuacion, payload.get("acta_inspeccion_num"), fecha_str, crear=True)
    attach_notificacion(actuacion, payload.get("notificacion"))
    attach_comprobacion(actuacion, payload.get("comprobacion"))
    attach_clausura(actuacion, payload.get("clausura"), crear=True)
    attach_decomiso(actuacion, payload.get("decomiso"), crear=True)

    db.session.flush()

    # 7) Oficio + Expediente (si vienen)
    oficio = attach_oficio(payload.get("oficio"))
    db.session.flush()

    comprobacion_id = actuacion.comprobacion_id
    oficio_id = oficio.id if oficio else None

    attach_expediente(payload.get("expediente"), comprobacion_id, oficio_id)

    db.session.commit()
    return actuacion


# =========================================================
# Service UPDATE
# =========================================================

def actualizar_actuacion_desde_payload(payload: Dict[str, Any]) -> Actuaciones:
    act_id = payload.get("id")
    if not act_id:
        raise ValueError("ID de actuación requerido para actualizar.")

    actuacion = Actuaciones.query.get(act_id)
    if not actuacion:
        raise ValueError("Actuación no encontrada.")

    fecha_str = payload.get("fecha_actuacion")
    if fecha_str:
        mes, anio, fecha_date = parse_fecha_grid(fecha_str)
        actuacion.fecha = fecha_date
        actuacion.mes = mes
        actuacion.anio = anio

    # OT: si querés permitir cambiarla
    ot = get_or_create_orden_trabajo(payload["orden_trabajo_numero"], fecha_str or payload.get("fecha_actuacion") or "")
    db.session.flush()

    # si esa OT está usada por otra actuación
    otra = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
    if otra and otra.id != actuacion.id:
        raise ValueError("Esa Orden de Trabajo ya está asociada a otra actuación.")

    actuacion.orden_trabajo_id = ot.id

    # Campos simples
    if payload.get("tipo_actuacion") is not None:
        actuacion.tipo = payload["tipo_actuacion"]

    if payload.get("contraproducencia") is not None:
        actuacion.contraproducencia = payload["contraproducencia"]

    # Rubro + contrib + domicilio
    rubro = get_or_create_rubro(payload.get("rubro_nombre"))
    contrib = resolve_contribuyente(payload.get("contribuyente"))
    db.session.flush()

    domicilio = get_or_create_domicilio(payload.get("domicilio"), contrib, rubro)
    db.session.flush()

    if domicilio:
        actuacion.domicilio_id = domicilio.id

    # Inspectores
    nombres = payload.get("inspectores") or []
    if nombres:
        actuacion.inspector = get_inspectores_o_falla(nombres)

    # ✅ Actas: ahora EDITAN la asociada
    attach_inspeccion(actuacion, payload.get("acta_inspeccion_num"), fecha_str, crear=False)
    attach_notificacion(actuacion, payload.get("notificacion"))
    attach_comprobacion(actuacion, payload.get("comprobacion"))
    attach_clausura(actuacion, payload.get("clausura"), crear=False)
    attach_decomiso(actuacion, payload.get("decomiso"), crear=False)

    db.session.flush()

    # Oficio + Expediente
    oficio = attach_oficio(payload.get("oficio"))
    db.session.flush()

    comprobacion_id = actuacion.comprobacion_id
    oficio_id = oficio.id if oficio else None

    attach_expediente(payload.get("expediente"), comprobacion_id, oficio_id)

    db.session.commit()
    return actuacion
    """
    Actualiza una actuación a partir del payload del mapper.

    Identidad:
    - buscamos la actuación por OT (numero_acta + anio derivado de fecha).

    Filosofía simple:
    - si viene un dato en el payload, lo aplicamos.
    - no borramos cosas si no vienen.
    """
    """"
    borrar si no anda
    
    """""
    act_id = payload.get("id")
    if not act_id:
        raise ValueError("ID de actuación requerido para actualizar.")

    actuacion = Actuaciones.query.get(act_id)
    if not actuacion:
        raise ValueError("Actuación no encontrada.")
    
    fecha_str = payload.get("fecha_actuacion")
    if fecha_str:
        mes, anio, fecha_date = parse_fecha_grid(fecha_str)
        actuacion.fecha = fecha_date
        actuacion.mes = mes
        actuacion.anio = anio

    # 1) OT (si no existe, la creamos igual)
    ot = get_or_create_orden_trabajo(payload["orden_trabajo_numero"], fecha_str)
    db.session.flush()

    # 2) Debe existir actuación para editar
    actuacion = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
    if not actuacion:
        raise ValueError("No existe actuación para esa Orden de Trabajo.")

    # 3) Campos simples
    if payload.get("tipo_actuacion") is not None:
        actuacion.tipo = payload["tipo_actuacion"]

    if payload.get("contraproducencia") is not None:
        actuacion.contraproducencia = payload["contraproducencia"]

    # 4) Resolver rubro + contrib + domicilio
    rubro = get_or_create_rubro(payload.get("rubro_nombre"))
    contrib = resolve_contribuyente(payload.get("contribuyente"))
    db.session.flush()

    domicilio = get_or_create_domicilio(payload.get("domicilio"), contrib, rubro)
    db.session.flush()

    if domicilio:
        actuacion.domicilio_id = domicilio.id

    # 5) Inspectores
    nombres = payload.get("inspectores") or []
    if nombres:
        actuacion.inspector = get_inspectores_o_falla(nombres)

    # 6) Actas (en update no chequeamos unicidad “contra otra actuación”
    # porque en tu UI la edición es sobre lo ya existente)
    attach_inspeccion(actuacion, payload.get("acta_inspeccion_num"), fecha_str, crear=False)
    attach_notificacion(actuacion, payload.get("notificacion"))
    attach_comprobacion(actuacion, payload.get("comprobacion"))
    attach_clausura(actuacion, payload.get("clausura"), crear=False)
    attach_decomiso(actuacion, payload.get("decomiso"), crear=False)

    db.session.flush()

    # 7) Oficio + Expediente
    oficio = attach_oficio(payload.get("oficio"))
    db.session.flush()

    comprobacion_id = actuacion.comprobacion_id
    oficio_id = oficio.id if oficio else None

    attach_expediente(payload.get("expediente"), comprobacion_id, oficio_id)

    db.session.commit()
    return actuacion


# =========================================================
# Service DELETE
# =========================================================

def vincular_expediente_desde_actuacion(actuacion_id: int, data: Dict[str, Any]) -> Actuaciones:
    """
    Endpoint micro:
    Vincula/crea expediente asociado a la comprobación de la actuación.

    Espera:
    {
      "expediente_numero": "...",
      "expediente_anio": 2025
    }
    """

    actuacion = Actuaciones.query.get(actuacion_id)
    if not actuacion:
        raise ValueError("Actuación no encontrada.")

    # debe existir comprobación para poder colgar expediente
    if not actuacion.comprobacion_id:
        raise ValueError("Esta actuación no tiene acta de comprobación vinculada.")

    numero = data.get("expediente_numero")
    anio = data.get("expediente_anio")

    if not numero or anio is None:
        raise ValueError("expediente_numero y expediente_anio son obligatorios.")

    # reutilizamos tu helper existente
    attach_expediente(
        {"numero": numero, "anio": anio},
        comprobacion_id=actuacion.comprobacion_id,
        oficio_id=None,  # en esta etapa no tocamos oficio
    )

    db.session.commit()
    return actuacion


def eliminar_actuacion(actuacion_id: int) -> None:
    """
    Elimina una actuación por ID.

    OJO:
    - Tenés cascades 1 a 1 en varias tablas, así que se van
      a borrar también clausura/decomiso/inspeccion si las configuraste así.
    """
    actuacion = Actuaciones.query.get(actuacion_id)
    if not actuacion:
        raise ValueError("Actuación no encontrada.")

    db.session.delete(actuacion)
    db.session.commit()
