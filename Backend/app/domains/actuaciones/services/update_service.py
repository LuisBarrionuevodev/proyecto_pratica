from __future__ import annotations

from typing import Any, Dict

from app.database import db
from app.models import Actuaciones, Domicilio, Oficio, Expediente
from app.utils.fechas import parse_fecha_grid

from .previas_service import resolver_previas
from app.domains.actuaciones.attach.inspeccion import attach_inspeccion
from app.domains.actuaciones.services.completar_trabajo_actas_service import (
    aplicar_notificacion_y_comprobacion_completar_trabajo,
)
from app.domains.actuaciones.attach.clausura import attach_clausura
from app.domains.actuaciones.attach.decomiso import attach_decomiso
from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.domicilios.services.domicilio_update_service import aplicar_edicion_domicilio_operativo
from app.domains.domicilios.services.domicilio_completar_trabajo_service import (
    heredar_geocode_domicilio_desde_origen,
    relevamiento_id_desde_actuacion,
)
from app.domains.domicilios.utils.preservar_geocode_domicilio import (
    preservar_geocode_existente_al_editar_domicilio,
    snapshot_domicilio_geocode,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.domicilios.services.domicilio_edit_policy_service import (
    domicilio_payload_cambia_texto_geografico,
)
from app.domains.actuaciones.attach.orden_trabajo import get_or_create_orden_trabajo
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
from app.domains.establecimientos.services.vincular_establecimiento_operativo_actuacion_service import (
    try_vincular_establecimiento_operativo_desde_actuacion,
)
from app.domains.actuaciones.cleanup.garbage_collector import (
    soft_delete_contribuyente_if_orphan,
    soft_delete_domicilio_if_orphan,
    soft_delete_notificacion_if_orphan,
    soft_delete_comprobacion_if_orphan,
    soft_delete_oficio_if_orphan,
    soft_delete_expediente_if_orphan,
)
from app.domains.actuaciones.services.actas_canal_payload_guard import (
    rechazar_oficio_expediente_en_payload_canal_actas,
)
from app.domains.actuaciones.services.expediente_actas_edit_guard import (
    assert_canal_actas_permite_payload_notificacion_comprobacion,
)
from app.domains.actuaciones.audit.inspectores_actuaciones_audit import (
    log_truncation_risk_if_applicable,
)
from app.domains.actuaciones.services.cargar_actuacion_post_commit import (
    ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal,
)
from app.domains.actuaciones.services.actuacion_corregir_cierre_operativo_service import (
    CorregirCierreOperativoError,
    aplicar_sincronizacion_tras_limpiar_contraproducencia,
    assert_puede_limpiar_contraproducencia,
)
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    assert_puede_editar_domicilio_actuacion,
    puede_editar_domicilio_actuacion,
    resolve_iniciador_operativo_actuacion,
)


def _norm_dom_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _domicilio_cambios_explicitos_crud(
    dom_actual: Domicilio | None,
    dom_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Completa calle/número en corrección CRUD para no mezclar texto viejo con campo nuevo (PR7.15b).

    ``aplicar_edicion_domicilio_operativo`` exige ambos campos cuando hay cambio geo.
    """
    cambios = dict(dom_payload or {})
    if dom_actual is None:
        return cambios
    calle = _norm_dom_str(cambios.get("calle"))
    numero = _norm_dom_str(cambios.get("numero"))
    if calle and not numero:
        cambios["numero"] = dom_actual.numero
    elif numero and not calle:
        cambios["calle"] = dom_actual.calle
    return cambios


def _get_actuacion_or_404(actuacion_id: int) -> Actuaciones:
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise ValueError("Actuación no encontrada.")
    return act


def aplicar_payload_actuacion(
    act: Actuaciones,
    payload: Dict[str, Any],
    *,
    ejecutar_resolver_previas: bool = True,
) -> None:
    """
    Aplica sobre una `Actuaciones` ya cargada las mismas mutaciones que el núcleo de
    `actualizar_actuacion`, **sin** `commit`, cleanup ni geocode.

    Sirve para orquestar en una sola transacción (p. ej. Completar trabajo + ruta ítem)
    reutilizando la lógica de domicilio, inspectores y actas. Oficio y expediente
    administrativo quedan fuera de este payload (ver `actas_canal_payload_guard`).

    Parámetros:
        act: instancia ORM persistida (con `id`).
        payload: dict canónico como el del mapper de grilla / update actuaciones.
        ejecutar_resolver_previas: si False, no invoca `resolver_previas` (flujos sin previas,
            p. ej. Completar trabajo).

    Errores:
        ValueError y demás excepciones de negocio de los attach/catalogs, igual que antes.

    Side effects:
        Modifica `act` y entidades relacionadas en la sesión actual; no hace flush/commit.
    """
    rechazar_oficio_expediente_en_payload_canal_actas(payload)

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

    # Nombre de fantasía del local (columna en actuaciones)
    if "nombre_local" in payload:
        raw_nl = payload.get("nombre_local")
        act.nombre_local = (str(raw_nl).strip() or None) if raw_nl is not None else None

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
        dom_payload = payload.get("domicilio") or {}
        ini_operativo = (
            resolve_iniciador_operativo_actuacion(int(act.id)) if getattr(act, "id", None) else None
        )
        puede_editar_dom, motivo_dom = puede_editar_domicilio_actuacion(act, ini_operativo)
        if not puede_editar_dom and (dom_payload.get("calle") or dom_payload.get("numero")):
            raise ValueError(motivo_dom or "No se puede editar el domicilio de esta actuación.")
        # si mandan domicilio, exige que rubro/contrib estén presentes o ya existan
        if rubro is None:
            rubro = get_rubro_o_falla(payload.get("rubro_nombre"))
        if contrib is None:
            contrib = resolve_contribuyente(payload.get("contribuyente"))

        # Permitir domicilio sin rubro/contribuyente si no hay tipo y sí contraproducencia
        allow_missing_catalogs = payload.get("tipo_actuacion") is None and payload.get("contraproducencia") is not None
        dom_actual = db.session.get(Domicilio, int(act.domicilio_id)) if act.domicilio_id else None
        texto_cambia = domicilio_payload_cambia_texto_geografico(dom_actual, dom_payload)
        if texto_cambia:
            assert_puede_editar_domicilio_actuacion(act, ini_operativo)
        cambios_domicilio = dom_payload if texto_cambia or dom_actual is None else {}
        if puede_editar_dom and texto_cambia and dom_actual is not None:
            cambios_domicilio = _domicilio_cambios_explicitos_crud(dom_actual, cambios_domicilio)
        relevamiento_id = relevamiento_id_desde_actuacion(int(act.id)) if getattr(act, "id", None) else None
        domicilio_id_anterior = act.domicilio_id
        geo_snapshot = (
            snapshot_domicilio_geocode(int(dom_actual.id)) if dom_actual is not None else None
        )

        outcome = aplicar_edicion_domicilio_operativo(
            domicilio_id_actual=act.domicilio_id,
            cambios=cambios_domicilio,
            contribuyente=contrib,
            rubro=rubro,
            contexto="ACTUACION",
            origen_id=int(act.id) if getattr(act, "id", None) else 0,
            modo_explicito=payload.get("modo_domicilio"),
            allow_missing_catalogs=allow_missing_catalogs,
            relevamiento_id=relevamiento_id,
        )
        dom = outcome.domicilio
        act.domicilio_id = dom.id if dom else None
        act.domicilio = dom
        if dom and isinstance(dom, Domicilio) and cambios_domicilio and texto_cambia:
            normalizar_domicilio_en_sesion(
                dom, override_numero_tipo=cambios_domicilio.get("numero_tipo")
            )
            if outcome.domicilio_id_cambio and domicilio_id_anterior is not None:
                heredar_geocode_domicilio_desde_origen(
                    int(domicilio_id_anterior), int(dom.id)
                )
            elif geo_snapshot is not None:
                preservar_geocode_existente_al_editar_domicilio(int(dom.id), geo_snapshot)

    # Inspectores
    if "inspectores" in payload:
        raw_ins = payload.get("inspectores") or []
        nombres = [str(x).strip() for x in raw_ins if str(x).strip()]
        if getattr(act, "id", None):
            log_truncation_risk_if_applicable(
                actuacion_id=int(act.id),
                payload_inspectores_nombres=nombres,
            )
        act.inspector = get_inspectores_o_falla(nombres) if nombres else []

    if ejecutar_resolver_previas:
        resolver_previas(act, payload)

    # Actas (update)
    if "acta_inspeccion_num" in payload:
        attach_inspeccion(act, payload.get("acta_inspeccion_num"), crear=False)

    if "notificacion" in payload or "comprobacion" in payload:
        aplicar_notificacion_y_comprobacion_completar_trabajo(
            act,
            notificacion=payload.get("notificacion") if "notificacion" in payload else None,
            comprobacion=payload.get("comprobacion") if "comprobacion" in payload else None,
        )

    if "clausura" in payload:
        attach_clausura(act, payload.get("clausura"), crear=False)

    if "decomiso" in payload:
        attach_decomiso(act, payload.get("decomiso"), crear=False)


def actualizar_actuacion(actuacion_id: int, payload: Dict[str, Any]) -> Actuaciones:
    """
    Actualiza una `Actuaciones` existente desde el canal **CargarActuacion** (PUT grilla).

    Payload: mismo canon que el alta por grilla; oficio/expediente administrativo van por endpoints
    dedicados.

    Este service mantiene el comportamiento histórico:
    - Aplica updates parciales según keys presentes en `payload`.
    - Recalcula `mes/anio/fecha` si viene `fecha_actuacion`.
    - Permite cambiar OT si vienen `orden_trabajo_numero` + `fecha_actuacion` (y respeta la regla 1 OT -> 1 actuación).
    - Delega el núcleo de mutación a `aplicar_payload_actuacion` (misma semántica histórica).
    - Tras aplicar el payload, intenta vincular ``establecimiento_operativo_id`` si corresponde
      (``try_vincular_establecimiento_operativo_desde_actuacion``).
    - Persiste con `db.session.commit()` al final.

    Cleanup post-update (soft delete):
    - Antes de modificar la actuación, guarda `old_domicilio_id` y el `old_contribuyente_id`
      (derivado del domicilio viejo si existe).
    - Luego del primer commit:
      - Si cambió `domicilio_id`, intenta soft-delete del domicilio viejo si quedó huérfano.
      - Siempre evalúa soft-delete del contribuyente viejo (si existe) para cubrir reasignaciones
        por cambio de DNI, aun cuando no cambie `domicilio_id`.
      - Hace un segundo commit para persistir `deleted_at`.

    Args:
        actuacion_id: id de la actuación a actualizar.
        payload: dict canon del mapper (sin DB).

    Returns:
        Instancia de `Actuaciones` actualizada y commiteada.

    Raises:
        ValueError: si la actuación no existe o si se violan reglas de negocio/validaciones.
    """
    act = _get_actuacion_or_404(actuacion_id)

    # Snapshot pre-update para cleanup post-commit.
    old_domicilio_id: int | None = act.domicilio_id
    old_contribuyente_id: int | None = None
    old_orden_trabajo_id: int | None = act.orden_trabajo_id  # nuevo: para soft delete OT
    old_notificacion_id: int | None = act.notificacion_id
    old_comprobacion_id: int | None = act.comprobacion_id
    old_oficios_ids: list[int] = []
    old_expedientes_ids: list[int] = []
    if old_comprobacion_id:
        old_oficios_ids = [o.id for o in Oficio.query.filter_by(comprobacion_id=old_comprobacion_id).all()]
        old_expedientes_ids = [e.id for e in Expediente.query.filter_by(comprobacion_id=old_comprobacion_id).all()]
    if old_domicilio_id is not None:
        old_dom: Domicilio | None = db.session.get(Domicilio, old_domicilio_id)
        if old_dom is not None:
            old_contribuyente_id = old_dom.contribuyente_id

    limpiar_contra = bool(payload.get("limpiar_contraproducencia"))
    item_correccion = None
    ini_correccion = None
    if limpiar_contra:
        item_correccion, ini_correccion = assert_puede_limpiar_contraproducencia(act)

    assert_canal_actas_permite_payload_notificacion_comprobacion(act, payload)
    aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=True)

    if limpiar_contra:
        aplicar_sincronizacion_tras_limpiar_contraproducencia(
            act,
            item=item_correccion,
            ini=ini_correccion,
        )

    try_vincular_establecimiento_operativo_desde_actuacion(
        act,
        created_by_user_id=get_current_user_id_or_fallback(),
    )

    db.session.add(act)
    db.session.commit()

    # PR7.15: corrección de domicilio desde CRUD no propaga a iniciadores (solo relevamiento base editable).
    if act.domicilio_id and old_domicilio_id == act.domicilio_id:
        # STAB-7: corrección in-place — datos actualizados en la misma fila de domicilio.
        pass

    # Garbage collector post-update:
    # - si cambió el domicilio, intentar soft-delete del domicilio viejo si quedó huérfano.
    # - siempre evaluar el contribuyente viejo (si existe) para cubrir reasignaciones por DNI.
    ran_cleanup = False
    if old_domicilio_id is not None and old_domicilio_id != act.domicilio_id:
        soft_delete_domicilio_if_orphan(old_domicilio_id)
        ran_cleanup = True
    if old_contribuyente_id is not None:
        soft_delete_contribuyente_if_orphan(old_contribuyente_id)
        ran_cleanup = True
    if old_orden_trabajo_id is not None and old_orden_trabajo_id != act.orden_trabajo_id:
        # soft delete de OT viejo si quedó huérfano
        from app.domains.actuaciones.cleanup.garbage_collector import soft_delete_orden_id_orphan
        soft_delete_orden_id_orphan(old_orden_trabajo_id)
        ran_cleanup = True
    if old_notificacion_id is not None and old_notificacion_id != act.notificacion_id:
        soft_delete_notificacion_if_orphan(old_notificacion_id)
        ran_cleanup = True
    if old_comprobacion_id is not None and old_comprobacion_id != act.comprobacion_id:
        soft_delete_comprobacion_if_orphan(old_comprobacion_id)
        for oid in old_oficios_ids:
            soft_delete_oficio_if_orphan(oid)
        for eid in old_expedientes_ids:
            soft_delete_expediente_if_orphan(eid)
        ran_cleanup = True

    if ran_cleanup:
        db.session.commit()

    ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal()
    return act
