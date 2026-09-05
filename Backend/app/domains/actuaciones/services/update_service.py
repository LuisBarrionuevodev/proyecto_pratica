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
from app.domains.domicilios.services.domicilio_update_service import (
    aplicar_edicion_domicilio_operativo,
    _aplicar_rubro_contrib_seguro,
)
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
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    domicilio_puede_resolver_establecimiento_operativo,
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
    rechazar_campos_operativos_oficio_en_put_canal_actas,
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
from app.domains.actuaciones.services.actuacion_reencolado_service import (
    assert_actuacion_editable_sin_intento_posterior,
    procesar_establecimiento_contraproducencia_desde_put,
)
from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
    assert_puede_editar_domicilio_actuacion,
    assert_puede_editar_rubro_actuacion,
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


def _actuacion_id_int(act: Actuaciones) -> int | None:
    """Id persistido de la actuación; ignora mocks u otros valores no enteros."""
    raw = getattr(act, "id", None)
    return raw if isinstance(raw, int) else None


def _domicilio_id_int(act: Actuaciones) -> int | None:
    """FK domicilio persistida; ignora mocks u otros valores no enteros."""
    raw = getattr(act, "domicilio_id", None)
    return raw if isinstance(raw, int) else None


def _sincronizar_domicilio_relevamiento_direccion_incorrecta_si_aplica(
    act: Actuaciones,
    *,
    domicilio_id_anterior: int | None,
    limpiar_contra: bool,
) -> None:
    """
    GESTIÓN-FIX.10A.2-B: alinea relevamiento origen e iniciador activo cuando, tras
    ``DIRECCION INCORRECTA``, el PUT de actuación cambia ``domicilio_id``.

    Parámetros:
        act: actuación ya mutada por ``aplicar_payload_actuacion``.
        domicilio_id_anterior: FK domicilio antes del PUT.
        limpiar_contra: si True, no propaga (contra removida en el mismo request).

    Errores:
        No lanza; omite silenciosamente si no aplica la policy.
    """
    if limpiar_contra:
        return

    domicilio_id_nuevo = _domicilio_id_int(act)
    if domicilio_id_nuevo is None or domicilio_id_anterior == domicilio_id_nuevo:
        return

    from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
        es_contraproducencia_correctiva_direccion,
    )

    if not es_contraproducencia_correctiva_direccion(act.contraproducencia):
        return

    actuacion_id = _actuacion_id_int(act)
    if actuacion_id is None:
        return

    ini = resolve_iniciador_operativo_actuacion(actuacion_id)
    if ini is None or (ini.tipo_iniciador or "").strip().upper() != "RELEVAMIENTO":
        return

    from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
        estados_propagables_domicilio,
        propagar_domicilio_a_iniciadores_activos,
    )
    from app.models import Relevamiento

    estado = (ini.estado_iniciador or "").strip().upper()
    if estado not in estados_propagables_domicilio():
        return

    if not ini.relevamiento_id:
        return

    rel = db.session.get(Relevamiento, int(ini.relevamiento_id))
    if rel is None:
        return

    rel.domicilio_id = domicilio_id_nuevo
    db.session.add(rel)
    propagar_domicilio_a_iniciadores_activos(
        "RELEVAMIENTO",
        int(rel.id),
        int(domicilio_id_nuevo),
    )
    if ini.domicilio_id is None or int(ini.domicilio_id) != int(domicilio_id_nuevo):
        ini.domicilio_id = domicilio_id_nuevo
        db.session.add(ini)


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

    from app.domains.actuaciones.services.oficio_circuito_service import (
        actuacion_es_circuito_reinspeccion_oficio,
    )

    act_id = _actuacion_id_int(act)
    domicilio_id_int = _domicilio_id_int(act)
    es_oficio_circuito = act_id is not None and actuacion_es_circuito_reinspeccion_oficio(act_id)

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
    if "nombre_local" in payload and not es_oficio_circuito:
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
    rubro = (
        get_rubro_o_falla(payload.get("rubro_nombre"))
        if "rubro_nombre" in payload and not es_oficio_circuito
        else None
    )
    contrib = None
    contrib_clear = False
    if "contribuyente" in payload and not es_oficio_circuito:
        if payload.get("contribuyente") is None:
            contrib_clear = True
        else:
            contrib = resolve_contribuyente(payload.get("contribuyente"))
    if "domicilio" in payload and not es_oficio_circuito:
        dom_payload = payload.get("domicilio") or {}
        ini_operativo = resolve_iniciador_operativo_actuacion(act_id) if act_id else None
        puede_editar_dom, motivo_dom = puede_editar_domicilio_actuacion(act, ini_operativo)
        if not puede_editar_dom and (dom_payload.get("calle") or dom_payload.get("numero")):
            raise ValueError(motivo_dom or "No se puede editar el domicilio de esta actuación.")
        # si mandan domicilio, exige que rubro/contrib estén presentes o ya existan
        if rubro is None:
            rubro = get_rubro_o_falla(payload.get("rubro_nombre"))
        if contrib is None and not contrib_clear and payload.get("contribuyente"):
            contrib = resolve_contribuyente(payload.get("contribuyente"))

        # Permitir domicilio sin rubro/contribuyente si no hay tipo y sí contraproducencia
        allow_missing_catalogs = payload.get("tipo_actuacion") is None and payload.get("contraproducencia") is not None
        dom_actual = db.session.get(Domicilio, domicilio_id_int) if domicilio_id_int else None
        texto_cambia = domicilio_payload_cambia_texto_geografico(dom_actual, dom_payload)
        if texto_cambia:
            assert_puede_editar_domicilio_actuacion(act, ini_operativo)
        cambios_domicilio = dom_payload if texto_cambia or dom_actual is None else {}
        if puede_editar_dom and texto_cambia and dom_actual is not None:
            cambios_domicilio = _domicilio_cambios_explicitos_crud(dom_actual, cambios_domicilio)
        relevamiento_id = relevamiento_id_desde_actuacion(act_id) if act_id else None
        domicilio_id_anterior = domicilio_id_int
        geo_snapshot = (
            snapshot_domicilio_geocode(int(dom_actual.id)) if dom_actual is not None else None
        )

        outcome = aplicar_edicion_domicilio_operativo(
            domicilio_id_actual=domicilio_id_int,
            cambios=cambios_domicilio,
            contribuyente=contrib,
            rubro=rubro,
            contexto="ACTUACION",
            origen_id=act_id or 0,
            modo_explicito=payload.get("modo_domicilio"),
            allow_missing_catalogs=allow_missing_catalogs,
            relevamiento_id=relevamiento_id,
            limpiar_contribuyente=contrib_clear,
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

    elif not es_oficio_circuito and domicilio_id_int:
        dom_actual = db.session.get(Domicilio, domicilio_id_int)
        if dom_actual is None:
            raise ValueError("Domicilio de la actuación no encontrado.")
        hay_cambio_real_rubro = rubro is not None and (
            dom_actual.rubro_id is None or int(dom_actual.rubro_id) != int(rubro.id)
        )
        hay_cambio_real_contrib = (not contrib_clear) and contrib is not None and (
            dom_actual.contribuyente_id is None
            or int(dom_actual.contribuyente_id) != int(contrib.id)
        )
        if contrib_clear and dom_actual.contribuyente_id is not None:
            dom = _aplicar_rubro_contrib_seguro(
                dom_actual,
                contribuyente=None,
                rubro=None,
                numero_tipo=None,
                contexto="ACTUACION",
                origen_id=act_id,
                limpiar_contribuyente=True,
            )
            act.domicilio_id = dom.id
            act.domicilio = dom
        elif hay_cambio_real_rubro or hay_cambio_real_contrib:
            ini_operativo = resolve_iniciador_operativo_actuacion(act_id) if act_id else None
            if hay_cambio_real_rubro:
                assert_puede_editar_rubro_actuacion(act, ini_operativo)
            from app.domains.domicilios.services.domicilio_update_service import _aplicar_rubro_contrib_seguro

            relevamiento_id = relevamiento_id_desde_actuacion(act_id) if act_id else None
            dom = _aplicar_rubro_contrib_seguro(
                dom_actual,
                contribuyente=contrib if hay_cambio_real_contrib else None,
                rubro=rubro if hay_cambio_real_rubro else None,
                numero_tipo=None,
                contexto="ACTUACION",
                origen_id=act_id,
            )
            act.domicilio_id = dom.id
            act.domicilio = dom

    # Inspectores
    if "inspectores" in payload:
        raw_ins = payload.get("inspectores") or []
        nombres = [str(x).strip() for x in raw_ins if str(x).strip()]
        if act_id:
            log_truncation_risk_if_applicable(
                actuacion_id=act_id,
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


def _resolver_establecimiento_operativo_tras_contraproducencia_put(act: Actuaciones) -> None:
    """
    Paridad acotada con Completar trabajo al establecer contraproducencia desde PUT.

    Qué hace:
        Si la actuación quedó con contraproducencia operativa y el domicilio final cumple
        ``identidad_logica_completa`` (FIX.7), delega en ``resolve_establecimiento_por_domicilio``.
        Si la identidad dejó de ser válida, desvincula ``establecimiento_operativo_id``.

    Parámetros:
        act: actuación ya mutada en sesión (payload + sync de contraproducencia aplicados).

    Retorno:
        None. Modifica ``act`` en memoria; sin commit.

    Errores:
        Ninguno explícito; integridad DB puede fallar al commit del llamador.
    """
    if not (act.contraproducencia or "").strip():
        return
    if act.domicilio_id is None:
        act.establecimiento_operativo_id = None
        return
    dom = db.session.get(Domicilio, act.domicilio_id)
    if not domicilio_puede_resolver_establecimiento_operativo(dom):
        act.establecimiento_operativo_id = None
        return
    eid = resolve_establecimiento_por_domicilio(
        int(act.domicilio_id),
        created_by_user_id=get_current_user_id_or_fallback(),
    )
    if eid is not None:
        act.establecimiento_operativo_id = eid


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
    - Si el PUT establece contraproducencia operativa, resuelve EO con la misma semántica que
      Completar trabajo (``resolve_establecimiento_por_domicilio`` sobre el domicilio final).
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
    assert_actuacion_editable_sin_intento_posterior(actuacion_id)

    from app.domains.actuaciones.services.oficio_circuito_service import (
        actuacion_es_circuito_reinspeccion_oficio,
    )

    if actuacion_es_circuito_reinspeccion_oficio(actuacion_id):
        identity_keys = (
            "rubro_nombre",
            "contribuyente",
            "domicilio",
            "calle",
            "numero",
            "numero_tipo",
            "doc_nro",
            "contrib_apellido",
            "contrib_nombre",
            "razon_social",
        )
        if any(k in payload and payload.get(k) not in (None, "") for k in identity_keys):
            raise ValueError(
                "No se puede modificar la identidad del establecimiento en una actuación "
                "de reinspección por oficio."
            )
        raw_nl = payload.get("nombre_local")
        if raw_nl is not None and str(raw_nl).strip():
            nl_norm = str(raw_nl).strip()
            actual_nl = (str(act.nombre_local).strip() if act.nombre_local else None) or None
            if nl_norm != (actual_nl or ""):
                raise ValueError(
                    "No se puede modificar la identidad del establecimiento en una actuación "
                    "de reinspección por oficio."
                )

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
    contra_anterior = (act.contraproducencia or "").strip()
    item_correccion = None
    ini_correccion = None
    ini_operativo = resolve_iniciador_operativo_actuacion(actuacion_id)
    rechazar_campos_operativos_oficio_en_put_canal_actas(
        act, payload, iniciador=ini_operativo
    )
    if limpiar_contra:
        item_correccion, ini_correccion = assert_puede_limpiar_contraproducencia(act)

    assert_canal_actas_permite_payload_notificacion_comprobacion(act, payload)

    actas_a_quitar = payload.pop("actas_a_quitar", None)
    if actas_a_quitar:
        from app.domains.actuaciones.services.actas_quitar_canal_actas_service import (
            quitar_actas_de_actuacion_en_sesion,
        )

        quitar_actas_de_actuacion_en_sesion(
            act,
            list(actas_a_quitar),
            tolerar_ausentes=True,
        )
        db.session.flush()
        db.session.expire(act)

    aplicar_payload_actuacion(act, payload, ejecutar_resolver_previas=True)

    if limpiar_contra:
        aplicar_sincronizacion_tras_limpiar_contraproducencia(
            act,
            item=item_correccion,
            ini=ini_correccion,
        )
    elif "contraproducencia" in payload:
        contra_nueva = (act.contraproducencia or "").strip()
        procesar_establecimiento_contraproducencia_desde_put(
            act,
            contra_anterior=contra_anterior,
            contra_nueva=contra_nueva,
        )
        _resolver_establecimiento_operativo_tras_contraproducencia_put(act)

    try_vincular_establecimiento_operativo_desde_actuacion(
        act,
        created_by_user_id=get_current_user_id_or_fallback(),
    )

    _sincronizar_domicilio_relevamiento_direccion_incorrecta_si_aplica(
        act,
        domicilio_id_anterior=old_domicilio_id,
        limpiar_contra=limpiar_contra,
    )

    db.session.add(act)
    db.session.commit()

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
