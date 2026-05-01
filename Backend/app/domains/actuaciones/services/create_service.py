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
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
from app.domains.establecimientos.services.vincular_establecimiento_operativo_actuacion_service import (
    try_vincular_establecimiento_operativo_desde_actuacion,
)
from app.domains.actuaciones.services.actas_canal_payload_guard import (
    rechazar_oficio_expediente_en_payload_canal_actas,
)


def _resolve_tipo_actuacion(payload: Dict[str, Any]) -> str | None:
    """
    Resuelve tipo_actuacion efectivo para altas desde grilla.

    Reglas:
    - Si el payload ya trae tipo_actuacion explícito, se respeta.
    - Si no trae tipo pero hay evidencia de inspección real (actas operativas),
      fuerza `INSPECCION` para mantener consistencia del circuito.
    - Si no hay evidencia, mantiene `None` (flujo contraproducencia/registro mínimo).
    """
    tipo = payload.get("tipo_actuacion")
    if tipo:
        return tipo

    notificacion = payload.get("notificacion") or {}
    comprobacion = payload.get("comprobacion") or {}
    clausura = payload.get("clausura") or {}
    decomiso = payload.get("decomiso") or {}

    has_inspeccion_real = any(
        [
            bool(payload.get("acta_inspeccion_num")),
            bool(notificacion.get("acta_num")),
            bool(comprobacion.get("acta_num")),
            bool(clausura.get("acta_num")),
            bool(decomiso.get("acta_num")),
        ]
    )
    if has_inspeccion_real:
        return "INSPECCION"

    return None


def crear_actuacion_desde_payload(payload: Dict[str, Any]) -> Actuaciones:
    """
    Crea una `Actuaciones` y adjunta entidades relacionadas según el payload canon.

    Canal: **CargarActuacion** (grilla). No persiste oficio ni expediente administrativo por
    este payload; esos circuitos son Esperando oficio / Esperando expediente.

    Este service mantiene el comportamiento histórico:
    - Determina `mes/anio/fecha` desde `fecha_actuacion`.
    - Crea/obtiene OT y aplica la regla "1 actuación por OT".
    - Resuelve catálogos (rubro/inspectores) y dominios (contribuyente/domicilio).
    - Resuelve previas (notificación/comprobación) y adjunta actas del día.
    - No adjunta oficio/expediente (flujos Esperando expediente / oficio).
    - Si hay domicilio y datos mínimos de ficha, intenta vincular ``establecimiento_operativo_id`` (ver
      ``try_vincular_establecimiento_operativo_desde_actuacion``); si no, queda para Completar trabajo.
    - Persiste con `db.session.commit()` al final.

    Args:
        payload: dict canon del mapper (sin DB).

    Returns:
        Instancia de `Actuaciones` creada y commiteada.

    Raises:
        ValueError: si se violan reglas de negocio (p.ej. OT duplicada, catálogos inexistentes, validaciones de actas).
    """
    rechazar_oficio_expediente_en_payload_canal_actas(payload)

    fecha_str = payload.get("fecha_actuacion")
    mes, anio, fecha = parse_fecha_grid(fecha_str)

    # OT
    ot = get_or_create_orden_trabajo(payload.get("orden_trabajo_numero"), fecha_str)

    # Regla: 1 actuación por OT
    existente = Actuaciones.query.filter_by(orden_trabajo_id=ot.id).first()
    if existente:
        raise ValueError("Ya existe una actuación asociada a esa Orden de Trabajo.")

    tipo_actuacion = _resolve_tipo_actuacion(payload)
    act = Actuaciones(
        fecha=fecha,
        mes=mes,
        anio=anio,
        tipo=tipo_actuacion,
        contraproducencia=payload.get("contraproducencia"),
        orden_trabajo_id=ot.id,
    )
    db.session.add(act)
    db.session.flush()  # necesitamos act.id para attach_* que dependen de actuacion_id

    # Catálogos / entidades base
    # Si no hay tipo y hay contraproducencia, permitimos domicilio sin rubro/contribuyente
    allow_missing_catalogs = tipo_actuacion is None and payload.get("contraproducencia") is not None
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

    try_vincular_establecimiento_operativo_desde_actuacion(
        act,
        created_by_user_id=get_current_user_id_or_fallback(),
    )

    db.session.add(act)
    db.session.commit()

    # Best-effort geocode (no bloquea la creación)
    try:
        if act.domicilio_id:
            on_domicilio_changed(act.domicilio_id)
    except Exception:
        pass
    return act
