from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, RutaGrupo, RutaGrupoInspector, RutaItem

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
    validar_tipo_actuacion_para_iniciador,
)
from app.domains.establecimientos.services.resolve_establecimiento_por_domicilio import (
    resolve_establecimiento_por_domicilio,
)
from app.models import CatalogTipoActuacion

from app.domains.actuaciones.catalogs.inspector import get_inspectores_o_falla

from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import (
    on_domicilio_changed,
)

_MSG_RESULTADO_SOLO_OFICIO = (
    "El resultado de cumplimiento del oficio solo aplica a REINSPECCION_OFICIO."
)
_MSG_RESULTADO_SOLO_VISITA_REALIZADA = (
    "El resultado de cumplimiento del oficio solo aplica cuando la visita está realizada "
    "(sin contraproducencia)."
)


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
    - Si se envía valor: exige iniciador ``REINSPECCION_OFICIO`` y visita realizada (sin contraproducencia).
    """
    val = payload.resultado_cumplimiento_oficio
    if val is None:
        return
    if bucket != ContrapBucket.NONE:
        raise ValueError(_MSG_RESULTADO_SOLO_VISITA_REALIZADA)
    if ini.tipo_iniciador != "REINSPECCION_OFICIO":
        raise ValueError(_MSG_RESULTADO_SOLO_OFICIO)
    act.resultado_cumplimiento_oficio = val


def _apply_domicilio_rubro(
    act: Actuaciones,
    payload: CompletarTrabajoCierreIn | CompletarTrabajoCierreCompletoIn,
    *,
    bucket: ContrapBucket,
    ini: IniciadorRuta,
) -> None:
    """Replica la lógica mínima de PATCH para calle/número/rubro/contrib (sin commit)."""
    patch_keys = ("calle", "numero", "rubro_nombre")
    if not any(getattr(payload, k) is not None for k in patch_keys):
        return

    from app.domains.actuaciones.attach.domicilio import get_or_create_domicilio
    from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla

    rubro = None
    if payload.rubro_nombre is not None:
        rubro = get_rubro_o_falla(payload.rubro_nombre)
    elif act.domicilio and act.domicilio.rubro:
        rubro = act.domicilio.rubro

    contrib = None
    if act.domicilio and act.domicilio.contribuyente:
        contrib = act.domicilio.contribuyente

    dom_payload: dict[str, Any] = {}
    if payload.calle is not None:
        dom_payload["calle"] = payload.calle
    elif act.domicilio:
        dom_payload["calle"] = act.domicilio.calle
    elif ini.domicilio:
        dom_payload["calle"] = ini.domicilio.calle

    if payload.numero is not None:
        dom_payload["numero"] = payload.numero
    elif act.domicilio:
        dom_payload["numero"] = act.domicilio.numero
    elif ini.domicilio:
        dom_payload["numero"] = ini.domicilio.numero

    if not dom_payload:
        return

    # Visita no realizada: no exigir contribuyente/rubro aunque `act.tipo` ya venga seteado (p. ej. al publicar ruta).
    allow_missing_catalogs = bucket != ContrapBucket.NONE
    dom = get_or_create_domicilio(
        dom_payload,
        contrib,
        rubro,
        allow_missing_catalogs=allow_missing_catalogs,
    )
    act.domicilio_id = dom.id if dom else None


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

    stored_contra, bucket = normalize_contraproducencia(payload.contraproducencia)

    now = datetime.utcnow()

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
            _apply_domicilio_rubro(act, payload, bucket=bucket, ini=ini)
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
            _apply_domicilio_rubro(act, payload, bucket=bucket, ini=ini)
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
        elif bucket == ContrapBucket.NO_EXISTE_LOCAL:
            assert stored_contra is not None
            item.estado_ejecucion = "NO_REALIZADO"
            item.estado_ruta_item = "NO_REALIZADO"
            item.motivo_no_realizado = motivo_no_realizado_para_ruta_item(stored_contra, bucket)
            ini.estado_iniciador = "CERRADO_NO_EXISTE_LOCAL"
            ini.cerrado_at = now
            ini.cerrado_motivo = "NO_EXISTE_LOCAL"
        else:
            assert stored_contra is not None
            item.estado_ejecucion = "NO_REALIZADO"
            item.estado_ruta_item = "NO_REALIZADO"
            item.motivo_no_realizado = motivo_no_realizado_para_ruta_item(stored_contra, bucket)
            ini.estado_iniciador = "PENDIENTE"
            ini.prioridad = max(int(ini.prioridad), 5)
            ini.cerrado_at = None
            ini.cerrado_motivo = None

        if bucket == ContrapBucket.NONE:
            eid = resolve_establecimiento_por_domicilio(
                act.domicilio_id,
                created_by_user_id=ejecutado_por_user_id,
            )
            if eid is not None:
                act.establecimiento_operativo_id = eid

        ini.updated_at = now
        db.session.add(act)
        db.session.add(item)
        db.session.add(ini)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

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
        if dom_id:
            on_domicilio_changed(dom_id)
    except Exception:
        pass
    return ruta_item_completar_trabajo_to_row(fresh)
