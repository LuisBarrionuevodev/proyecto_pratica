from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.models import (
    Actuaciones,
    Domicilio,
    IniciadorRuta,
    Relevamiento,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
)
from app.models import Contribuyente

from app.domains.actuaciones.mappers.completar_trabajo_cierre_mapper import (
    map_completar_trabajo_cierre_to_aplicar_payload,
    map_no_permite_inspeccion_actas_to_aplicar_payload,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.schemas.completar_trabajo_cierre_in import CompletarTrabajoCierreIn
from app.domains.actuaciones.schemas.list_filters import _coerce_catalog_value
from app.domains.actuaciones.presenters.completar_trabajo_presenters import ruta_item_completar_trabajo_to_row
from app.domains.actuaciones.services.completar_trabajo_inspectores_grupo import (
    list_inspector_nombres_desde_ruta_item_grupo,
)
from app.domains.actuaciones.services.update_service import aplicar_payload_actuacion
from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    ContrapBucket,
    motivo_no_realizado_para_ruta_item,
    normalize_contraproducencia,
)
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    es_flujo_cumplimiento_oficio,
    es_flujo_verificar_informar,
    promover_iniciador_reinspeccion_oficio_segun_tipo,
    validar_tipo_actuacion_para_iniciador,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.models import CatalogTipoActuacion

from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla
from app.domains.actuaciones.utils.contraproducencia_por_tipo_iniciador import (
    contraproducencia_permitida_en_completar_trabajo,
)

_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")


def _iniciador_tiene_item_abierto_en_ruta_operativa(
    iniciador_id: int,
    *,
    excluir_ruta_item_id: int | None = None,
) -> bool:
    """
    True si el iniciador tiene otro ítem no finalizado en ruta PUBLICADA o EN_CURSO.

    Parámetros:
        iniciador_id: iniciador a evaluar.
        excluir_ruta_item_id: ítem que se está cerrando (no cuenta).

    Retorno:
        False si solo quedan ítems finalizados o la ruta no es operativa.
    """
    q = (
        RutaItem.query.join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item.in_(_ESTADOS_RUTA_ITEM_ABIERTOS),
            RutaTrabajo.estado_ruta.in_(("PUBLICADA", "EN_CURSO")),
        )
    )
    if excluir_ruta_item_id is not None:
        q = q.filter(RutaItem.id != int(excluir_ruta_item_id))
    return q.first() is not None


def _reencolar_iniciador_si_oficio_no_cumple(
    *,
    ini: IniciadorRuta,
    act: Actuaciones,
    item: RutaItem,
    now: datetime,
) -> None:
    """
    STAB-4: reinspección por oficio con resultado NO_CUMPLE vuelve a pendientes si no hay otra ruta activa.

    Conservador: no duplica iniciador; no reencola si queda otro ítem abierto en ruta operativa.
    """
    if not es_flujo_cumplimiento_oficio(ini.tipo_iniciador):
        return
    if getattr(act, "resultado_cumplimiento_oficio", None) != "NO_CUMPLE":
        return
    if _iniciador_tiene_item_abierto_en_ruta_operativa(ini.id, excluir_ruta_item_id=item.id):
        return
    _aplicar_reencolado_iniciador(ini, now, act=act, cerrado_motivo="OFICIO_NO_CUMPLE")


def _aplicar_reencolado_iniciador(
    ini: IniciadorRuta,
    now: datetime,
    *,
    act: Actuaciones | None = None,
    cerrado_motivo: str | None = None,
) -> None:
    """
    Devuelve un iniciador al backlog planificable con prioridad alta y fecha de reingreso actualizada.

    Parámetros:
        ini: iniciador a reactivar.
        now: timestamp de cierre (UTC naive, coherente con el resto del servicio).
        act: actuación del cierre; define ``fecha_origen`` operativa (mínimo hoy UTC).
        cerrado_motivo: traza opcional (p. ej. OFICIO_NO_CUMPLE); None limpia cierre previo.
    """
    hoy = now.date()
    act_fecha = getattr(act, "fecha", None) if act is not None else None
    fecha_reencolado = act_fecha if act_fecha is not None and act_fecha >= hoy else hoy

    ini.estado_iniciador = "PENDIENTE"
    ini.prioridad = max(int(ini.prioridad or 0), 5)
    ini.cerrado_at = None
    ini.cerrado_motivo = cerrado_motivo
    ini.fecha_origen = fecha_reencolado
    ini.anio = fecha_reencolado.year
    ini.mes = fecha_reencolado.month

from app.domains.actuaciones.services.cargar_actuacion_post_commit import (
    ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal,
)
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)

_MSG_RESULTADO_SOLO_OFICIO = (
    "El resultado de cumplimiento del oficio solo aplica a reinspección/ratificación por oficio."
)
_MSG_RESULTADO_SOLO_VISITA_REALIZADA = (
    "El resultado de cumplimiento del oficio solo aplica cuando la visita está realizada "
    "(sin contraproducencia)."
)
_MSG_RESULTADO_NO_VERIFICAR_INFORMAR = (
    "El resultado de cumplimiento del oficio no aplica a verificar e informar."
)
_MSG_ACTAS_NO_VERIFICAR_SIN_INSPECCION = (
    "Con verificar e informar sin nueva inspección no se deben cargar actas normales."
)


def _clean_str_cierre(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _persist_resultado_cumplimiento_oficio(
    act: Actuaciones,
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
    *,
    bucket: ContrapBucket,
) -> None:
    """
    Persiste ``Actuaciones.resultado_cumplimiento_oficio`` solo en el contexto válido.

    Reglas:
    - Si no se envía valor (``None``): no modifica la columna (permite NULL histórico).
    - Si se envía valor: exige iniciador de cumplimiento oficio/ratificación y visita realizada (sin contraproducencia).
    """
    val = payload.resultado_cumplimiento_oficio
    if val is None:
        return
    if bucket != ContrapBucket.NONE:
        raise ValueError(_MSG_RESULTADO_SOLO_VISITA_REALIZADA)
    if not es_flujo_cumplimiento_oficio(ini.tipo_iniciador):
        raise ValueError(_MSG_RESULTADO_SOLO_OFICIO)
    act.resultado_cumplimiento_oficio = val


def _validar_payload_verificar_informar(
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
) -> None:
    """
    Reglas PR10.2c: verificar e informar distingue nueva inspección sí/no.

    Parámetros:
        ini: iniciador del ítem.
        payload: body validado del cierre.

    Errores:
        ValueError: resultado de cumplimiento o actas incoherentes con el flujo.
    """
    if not es_flujo_verificar_informar(ini.tipo_iniciador, payload.tipo_actuacion):
        return
    if payload.resultado_cumplimiento_oficio is not None:
        raise ValueError(_MSG_RESULTADO_NO_VERIFICAR_INFORMAR)
    if payload.realizo_nueva_inspeccion is False:
        acta_campos = (
            payload.acta_inspeccion_num,
            payload.acta_notificacion_num,
            payload.acta_comprobacion_num,
            payload.acta_clausura_num,
            payload.acta_decomiso_num,
            payload.notificacion_motivo_1,
            payload.notificacion_motivo_2,
            payload.notificacion_motivo_3,
            payload.comprobacion_motivo,
            payload.decomiso_kilos_total,
        )
        if any(v not in (None, "") for v in acta_campos):
            raise ValueError(_MSG_ACTAS_NO_VERIFICAR_SIN_INSPECCION)


def _resolve_contribuyente_para_domicilio_cierre(
    act: Actuaciones,
    payload: CompletarTrabajoCierreIn | CompletarTrabajoCierreCompletoIn,
) -> Contribuyente | None:
    """
    Titular efectivo para get_or_create_domicilio en cierre Completar trabajo.

    Alineado al mapper de cierre: si el body trae datos de titular, se delega en
    ``resolve_contribuyente`` con el mismo diccionario que usaría la grilla; si no,
    se reutiliza el contribuyente ya vinculado al domicilio de la actuación.
    """
    from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente

    if isinstance(payload, CompletarTrabajoCierreCompletoIn):
        row = payload
        if row.doc_nro or row.contrib_apellido or row.contrib_nombre or row.razon_social:
            data: dict[str, Any] = {
                "doc_nro": _clean_str_cierre(row.doc_nro),
                "apellido": _clean_str_cierre(row.contrib_apellido),
                "nombre": _clean_str_cierre(row.contrib_nombre),
                "razon_social": _clean_str_cierre(row.razon_social),
            }
            return resolve_contribuyente(data)
    if act.domicilio and act.domicilio.contribuyente:
        return act.domicilio.contribuyente
    return None


def _domicilio_rubro_patch_solicitado(
    payload: CompletarTrabajoCierreIn | CompletarTrabajoCierreCompletoIn,
) -> bool:
    """True si el cierre trae datos que deben mutar domicilio/rubro/titular vía get_or_create."""
    if any(getattr(payload, k, None) is not None for k in ("calle", "numero", "rubro_nombre", "numero_tipo")):
        return True
    if isinstance(payload, CompletarTrabajoCierreCompletoIn):
        return any(
            getattr(payload, k, None) is not None
            for k in ("doc_nro", "contrib_apellido", "contrib_nombre", "razon_social")
        )
    return False


def _apply_domicilio_rubro(
    act: Actuaciones,
    payload: CompletarTrabajoCierreIn | CompletarTrabajoCierreCompletoIn,
    *,
    bucket: ContrapBucket,
    ini: IniciadorRuta,
) -> tuple[bool, bool]:
    """
    Replica la lógica mínima de PATCH para calle/número/rubro/contrib (sin commit).

    Retorna:
        Tupla (vinculó domicilio, geocode heredado por copy-on-write desde relevamiento).
    """
    if not _domicilio_rubro_patch_solicitado(payload):
        return False, False

    from app.domains.domicilios.services.domicilio_completar_trabajo_service import (
        construir_cambios_domicilio_desde_payload_cierre,
        resolver_domicilio_real_desde_completar_trabajo,
    )
    from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
    from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
        normalizar_domicilio_en_sesion,
    )

    rubro = None
    if payload.rubro_nombre is not None:
        rubro = get_rubro_o_falla(payload.rubro_nombre)
    elif act.domicilio and act.domicilio.rubro:
        rubro = act.domicilio.rubro

    contrib = _resolve_contribuyente_para_domicilio_cierre(act, payload)

    dom_payload = construir_cambios_domicilio_desde_payload_cierre(payload, act=act, ini=ini)

    if not dom_payload or not dom_payload.get("calle") or not dom_payload.get("numero"):
        return False, False

    # Visita no realizada: no exigir contribuyente/rubro aunque `act.tipo` ya venga seteado (p. ej. al publicar ruta).
    allow_missing_catalogs = bucket != ContrapBucket.NONE
    modo_domicilio = getattr(payload, "modo_domicilio", None)
    domicilio_id_ref = act.domicilio_id or (ini.domicilio_id if ini else None)
    relevamiento_id = int(ini.relevamiento_id) if ini and ini.relevamiento_id else None
    allow_missing_effective = allow_missing_catalogs or (
        relevamiento_id is not None and contrib is None
    )
    outcome = resolver_domicilio_real_desde_completar_trabajo(
        domicilio_origen_id=domicilio_id_ref,
        payload_cambios=dom_payload,
        contribuyente=contrib,
        rubro=rubro,
        act_id=int(act.id),
        relevamiento_id=relevamiento_id,
        modo_explicito=modo_domicilio,
        allow_missing_catalogs=allow_missing_effective,
    )
    dom = outcome.domicilio
    act.domicilio_id = dom.id if dom else None
    act.domicilio = dom
    if dom:
        normalizar_domicilio_en_sesion(dom, override_numero_tipo=dom_payload.get("numero_tipo"))
    geocode_heredado = bool(
        outcome.domicilio_id_cambio
        and domicilio_id_ref is not None
        and relevamiento_id is not None
    )
    return dom is not None, geocode_heredado


def _vincular_notificacion_reinspeccion_en_acta(
    *,
    act: Actuaciones,
    ini: IniciadorRuta,
    bucket: ContrapBucket,
) -> None:
    """
    REINSPECCION_NOTIFICACION realizada: enlaza ``notificacion_id`` en la acta de trabajo.

    Permite que ``list_reinspeccion_notificacion_operativas`` detecte la reinspección vía
    ``subq_reinsp`` aunque el acta se haya creado sin FK al publicar la ruta.
    """
    if bucket != ContrapBucket.NONE:
        return
    if ini.tipo_iniciador != "REINSPECCION_NOTIFICACION":
        return
    if ini.notificacion_id is None:
        return
    if act.notificacion_id is None:
        act.notificacion_id = ini.notificacion_id
    if act.tipo != "REINSPECCION":
        act.tipo = "REINSPECCION"


def cerrar_completar_trabajo_por_ruta_item(
    *,
    ruta_item_id: int,
    payload: CompletarTrabajoCierreCompletoIn,
    ejecutado_por_user_id: int,
) -> dict:
    """
    Cierra operativamente un trabajo del día: actuación + ruta_item + iniciador (una transacción).

    Parámetros:
        ruta_item_id: ítem de ruta en EN_PROCESO.
        payload: cierre PR2 extendido (fase 3): domicilio/contrib, actas si visita realizada.
        ejecutado_por_user_id: usuario que registra el cierre.

    Retorno:
        Dict presenter `ruta_item_completar_trabajo_to_row` tras persistir.

    Errores:
        LookupError: ítem o relaciones no encontradas.
        ValueError: estado inválido o validación de negocio.
    """
    item = (
        RutaItem.query.filter(RutaItem.id == ruta_item_id)
        .with_for_update()
        .options(
            joinedload(RutaItem.actuacion).selectinload(Actuaciones.inspector),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.orden_trabajo),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.domicilio),
            joinedload(RutaItem.ruta_trabajo),
            joinedload(RutaItem.ruta_grupo)
            .selectinload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
        .first()
    )
    if not item:
        raise LookupError("Ruta ítem no encontrado")

    ruta = item.ruta_trabajo
    if not ruta or ruta.estado_ruta != "PUBLICADA":
        raise ValueError("La ruta debe estar PUBLICADA para cerrar el trabajo.")

    if item.deleted_at is not None:
        raise ValueError("El ítem está eliminado.")

    if item.estado_ruta_item != "EN_PROCESO":
        raise ValueError(f"El ítem no está EN_PROCESO (estado actual: {item.estado_ruta_item}).")

    act = item.actuacion
    if not act or not item.actuacion_id:
        raise ValueError("El ítem no tiene actuación asociada.")

    ini = item.iniciador_ruta
    if not ini:
        raise ValueError("El ítem no tiene iniciador asociado.")

    validar_tipo_actuacion_para_iniciador(
        tipo_iniciador=ini.tipo_iniciador,
        tipo_actuacion=payload.tipo_actuacion,
    )
    _validar_payload_verificar_informar(ini, payload)

    stored_contra, bucket = normalize_contraproducencia(payload.contraproducencia)
    if bucket != ContrapBucket.NONE and stored_contra:
        if not contraproducencia_permitida_en_completar_trabajo(
            ini.tipo_iniciador,
            stored_contra,
            tipo_actuacion=payload.tipo_actuacion,
        ):
            raise ValueError(
                f"La contraproducencia {stored_contra!r} no aplica al tipo de trabajo "
                f"{ini.tipo_iniciador!r}."
            )

    now = datetime.utcnow()
    domicilio_id_inicial = act.domicilio_id
    domicilio_mutado = False
    domicilio_geocode_heredado = False

    try:
        # 1) Actuación
        if bucket == ContrapBucket.NONE:
            aplicar_payload = map_completar_trabajo_cierre_to_aplicar_payload(
                payload,
                act=act,
                ini=ini,
            )
            if "inspectores" not in aplicar_payload:
                nombres_grupo = list_inspector_nombres_desde_ruta_item_grupo(item)
                if nombres_grupo:
                    aplicar_payload["inspectores"] = nombres_grupo
            # Misma vía que correctivas: persistir domicilio/rubro/titular aquí y no repetir
            # en ``aplicar_payload_actuacion`` (evita desincronía ORM act.domicilio vs act.domicilio_id).
            dom_vinculado_por_apply, geo_heredado = _apply_domicilio_rubro(
                act, payload, bucket=bucket, ini=ini
            )
            if geo_heredado:
                domicilio_geocode_heredado = True
            if dom_vinculado_por_apply:
                domicilio_mutado = True
                aplicar_payload.pop("domicilio", None)
                aplicar_payload.pop("contribuyente", None)
                aplicar_payload.pop("rubro_nombre", None)
            aplicar_payload_actuacion(
                act,
                aplicar_payload,
                ejecutar_resolver_previas=False,
            )
        elif bucket == ContrapBucket.NO_PERMITE_INSPECCION:
            if payload.tipo_actuacion is not None:
                act.tipo = _coerce_catalog_value(
                    payload.tipo_actuacion,
                    CatalogTipoActuacion,
                    "tipo_actuacion",
                    strip_prefix="TIPO.",
                )
            act.contraproducencia = stored_contra
            dom_ok, geo_heredado = _apply_domicilio_rubro(act, payload, bucket=bucket, ini=ini)
            if geo_heredado:
                domicilio_geocode_heredado = True
            if dom_ok:
                domicilio_mutado = True
            if payload.inspectores is not None:
                nombres = payload.inspectores or []
                act.inspector = get_inspectores_o_falla(nombres) if nombres else []
            else:
                nombres_grupo = list_inspector_nombres_desde_ruta_item_grupo(item)
                if nombres_grupo:
                    act.inspector = get_inspectores_o_falla(nombres_grupo)
            extra_actas = map_no_permite_inspeccion_actas_to_aplicar_payload(payload)
            if extra_actas:
                aplicar_payload_actuacion(act, extra_actas, ejecutar_resolver_previas=False)
        else:
            if payload.tipo_actuacion is not None:
                act.tipo = _coerce_catalog_value(
                    payload.tipo_actuacion,
                    CatalogTipoActuacion,
                    "tipo_actuacion",
                    strip_prefix="TIPO.",
                )
            act.contraproducencia = stored_contra
            dom_ok, geo_heredado = _apply_domicilio_rubro(act, payload, bucket=bucket, ini=ini)
            if geo_heredado:
                domicilio_geocode_heredado = True
            if dom_ok:
                domicilio_mutado = True
            if payload.inspectores is not None:
                nombres = payload.inspectores or []
                act.inspector = get_inspectores_o_falla(nombres) if nombres else []
            else:
                nombres_grupo = list_inspector_nombres_desde_ruta_item_grupo(item)
                if nombres_grupo:
                    act.inspector = get_inspectores_o_falla(nombres_grupo)

        if payload.nombre_local is not None:
            act.nombre_local = str(payload.nombre_local).strip() or None

        if act.domicilio_id and ini.domicilio_id != act.domicilio_id:
            ini.domicilio_id = act.domicilio_id

        _persist_resultado_cumplimiento_oficio(act, ini, payload, bucket=bucket)

        # 2) RutaItem + Iniciador
        item.observaciones_ejecucion = payload.observaciones_ejecucion
        item.ejecutado_por_user_id = ejecutado_por_user_id
        item.ejecutado_at = now

        if bucket == ContrapBucket.NONE:
            item.estado_ejecucion = "REALIZADO"
            item.estado_ruta_item = "FINALIZADO"
            item.motivo_no_realizado = None
            ini.estado_iniciador = "CUMPLIDO"
            ini.cerrado_at = None
            ini.cerrado_motivo = None
            _reencolar_iniciador_si_oficio_no_cumple(ini=ini, act=act, item=item, now=now)
            _vincular_notificacion_reinspeccion_en_acta(act=act, ini=ini, bucket=bucket)
        elif bucket == ContrapBucket.NO_EXISTE_LOCAL:
            assert stored_contra is not None
            item.estado_ejecucion = "NO_REALIZADO"
            item.estado_ruta_item = "FINALIZADO"
            item.motivo_no_realizado = motivo_no_realizado_para_ruta_item(stored_contra, bucket)
            ini.estado_iniciador = "CERRADO_NO_EXISTE_LOCAL"
            ini.cerrado_at = now
            ini.cerrado_motivo = "NO_EXISTE_LOCAL"
        else:
            assert stored_contra is not None
            item.estado_ejecucion = "NO_REALIZADO"
            item.estado_ruta_item = "FINALIZADO"
            item.motivo_no_realizado = motivo_no_realizado_para_ruta_item(stored_contra, bucket)
            _aplicar_reencolado_iniciador(ini, now, act=act, cerrado_motivo=None)

        if domicilio_mutado and act.domicilio_id and getattr(act, "id", None):
            from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
                propagar_domicilio_a_iniciadores_activos,
            )

            propagar_domicilio_a_iniciadores_activos(
                "ACTUACION",
                int(act.id),
                int(act.domicilio_id),
            )

        if bucket == ContrapBucket.NONE:
            eid = resolve_establecimiento_por_domicilio(
                act.domicilio_id,
                created_by_user_id=ejecutado_por_user_id,
            )
            if eid is not None:
                act.establecimiento_operativo_id = eid

        promover_iniciador_reinspeccion_oficio_segun_tipo(ini, payload.tipo_actuacion)

        ini.updated_at = now
        db.session.add(act)
        db.session.add(item)
        db.session.add(ini)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal()

    # Recargar relaciones para presenter
    fresh = (
        RutaItem.query.filter(RutaItem.id == ruta_item_id)
        .options(
            joinedload(RutaItem.actuacion).selectinload(Actuaciones.inspector),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.orden_trabajo),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
            joinedload(RutaItem.ruta_grupo)
            .selectinload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
        .first()
    )
    if not fresh:
        raise RuntimeError("No se pudo recargar el ítem tras el cierre.")
    try:
        dom_id = fresh.actuacion.domicilio_id if fresh.actuacion else None
        # Copy-on-write desde relevamiento: geocode heredado, no re-geocodificar.
        if dom_id and dom_id != domicilio_id_inicial and not domicilio_geocode_heredado:
            on_domicilio_changed(dom_id)
    except Exception:
        pass
    return ruta_item_completar_trabajo_to_row(fresh)
