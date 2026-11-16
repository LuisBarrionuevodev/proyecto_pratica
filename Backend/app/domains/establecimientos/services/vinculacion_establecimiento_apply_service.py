"""Aplicación atómica de vinculación de ficha (existente o alta)."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.domains.actuaciones.attach.documento_identidad_errors import DocumentoIdentidadError
from app.domains.establecimientos.mappers.vinculacion_establecimiento_mapper import (
    contribuyente_publico_dict,
    fingerprint_vinculacion,
)
from app.domains.establecimientos.presenters.vinculacion_establecimiento_presenters import (
    apply_vinculacion_result_payload,
    preview_vinculacion_payload,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionAltaIn,
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.contribuyente_documento_unico_service import (
    MSG_DOC_EN_USO,
    adquirir_lock_documento,
    assert_documento_almacenable,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_AMBIGUEDAD,
    MSG_SIN_CONTRIB,
    assert_rol_puede_corregir,
    cargar_ficha_para_correccion,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_alta import (
    alta_desde_body,
    alta_key,
    crear_contribuyente_alta,
    documento_norm_body,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_resolver import (
    MSG_ALTA_REQUERIDA,
    MSG_CONFIRMAR,
    MSG_DESTINO_APARECIO,
    MSG_DOC_AMBIGUO,
    MSG_IDENTIDAD_INCOMPLETA,
    MSG_PREVIEW_STALE,
    MSG_SIN_DESTINO,
    MSG_SIN_FINGERPRINT,
    eo_canonico_destino_misma_direccion,
    eo_ids_contribuyente,
    lookalike_ids_destino,
    resolver_contribuyente_destino,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
)
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    eo_canonico_id_para_domicilio,
)
from app.models import Contribuyente, CorreccionEstablecimientoAudit, Domicilio, User


def aplicar_vinculacion_establecimiento(
    establecimiento_id: int,
    body: VinculacionEstablecimientoIn,
    *,
    actor: User,
) -> dict[str, Any]:
    """
    Reasigna la ficha a un contribuyente existente o crea uno y lo asocia.

    Parámetros:
        establecimiento_id: ficha seleccionada.
        body: documento + fingerprint + confirmado (+ alta si corresponde).
        actor: usuario JWT.

    Retorno:
        dict con applied, audit_id y el preview revalidado.

    Errores:
        400 falta confirmación/fingerprint, alta incompleta o destino inválido.
        409 alcance obsoleto, documento ambiguo, en uso o domicilio ambiguo.
        403/404 permiso o ficha.
        Rollback total si falla cualquier escritura (sin auditoría de éxito).
    """
    assert_rol_puede_corregir(actor)
    if body.confirmado is not True:
        raise CorreccionEstablecimientoError(MSG_CONFIRMAR)
    if not body.fingerprint:
        raise CorreccionEstablecimientoError(MSG_SIN_FINGERPRINT)

    try:
        return _aplicar_en_transaccion(establecimiento_id, body, actor)
    except Exception:
        db.session.rollback()
        raise


def _wrap_documento_error(exc: DocumentoIdentidadError) -> CorreccionEstablecimientoError:
    """Traduce errores de UNICIDAD.1 al canal de vinculación."""
    codigo = getattr(exc, "codigo", "") or ""
    if codigo == "DOCUMENTO_AMBIGUO":
        return CorreccionEstablecimientoConflictError(MSG_DOC_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")
    if codigo == "DOCUMENTO_EN_USO":
        return CorreccionEstablecimientoConflictError(MSG_DOC_EN_USO, codigo="DOCUMENTO_EN_USO")
    status = int(getattr(exc, "http_status", 400) or 400)
    if status == 409:
        return CorreccionEstablecimientoConflictError(exc.detail, codigo=codigo or "CONFLICTO")
    return CorreccionEstablecimientoError(exc.detail, codigo=codigo or "DOCUMENTO_INVALIDO")


def _fingerprint_existente(scope, dest: Contribuyente, documento: str) -> str:
    return fingerprint_vinculacion(
        establecimiento_id=int(scope.eo.id),
        origen_id=int(scope.contribuyente.id),
        destino_id=int(dest.id),
        domicilio_ids=scope.domicilio_ids_ficha,
        lookalike_ids=scope.lookalike_ids,
        modo="EXISTENTE",
        documento_norm=documento_norm_body(documento),
    )


def _fingerprint_alta(scope, documento: str, alta: VinculacionAltaIn) -> str:
    return fingerprint_vinculacion(
        establecimiento_id=int(scope.eo.id),
        origen_id=int(scope.contribuyente.id),
        destino_id=0,
        domicilio_ids=scope.domicilio_ids_ficha,
        lookalike_ids=scope.lookalike_ids,
        modo="ALTA",
        documento_norm=documento_norm_body(documento),
        alta_key=alta_key(alta),
    )


def _aplicar_en_transaccion(
    establecimiento_id: int,
    body: VinculacionEstablecimientoIn,
    actor: User,
) -> dict[str, Any]:
    scope = cargar_ficha_para_correccion(establecimiento_id, for_update=True)
    if scope.contribuyente is None:
        raise CorreccionEstablecimientoError(MSG_SIN_CONTRIB)
    if not scope.identity_completa:
        raise CorreccionEstablecimientoConflictError(
            MSG_IDENTIDAD_INCOMPLETA, codigo="IDENTIDAD_INCOMPLETA"
        )
    if scope.lookalike_ids:
        raise CorreccionEstablecimientoConflictError(MSG_AMBIGUEDAD, codigo="AMBIGUEDAD_DOMICILIO")

    try:
        norm = assert_documento_almacenable(body.documento)
        adquirir_lock_documento(norm)
    except DocumentoIdentidadError as exc:
        raise _wrap_documento_error(exc) from exc
    except CorreccionEstablecimientoConflictError:
        raise

    dest: Contribuyente | None
    try:
        dest = resolver_contribuyente_destino(
            body.documento, scope.contribuyente, for_update=True
        )
    except CorreccionEstablecimientoConflictError:
        raise
    except CorreccionEstablecimientoError as exc:
        if getattr(exc, "codigo", None) != "SIN_DESTINO":
            raise
        dest = None

    alta = alta_desde_body(body)
    if dest is not None:
        dest_look = lookalike_ids_destino(
            scope.domicilio,
            dest,
            exclude_domicilio_ids=scope.domicilio_ids_ficha,
        )
        if dest_look:
            raise CorreccionEstablecimientoConflictError(MSG_AMBIGUEDAD, codigo="AMBIGUEDAD_DOMICILIO")
        fp_ok = _fingerprint_existente(scope, dest, body.documento)
        if body.fingerprint == fp_ok:
            return _persistir_reasignacion(
                scope, body, actor, dest, alta=None, creo_contribuyente=False
            )
        if alta is not None and body.fingerprint == _fingerprint_alta(scope, body.documento, alta):
            raise CorreccionEstablecimientoConflictError(
                MSG_DESTINO_APARECIO, codigo="DESTINO_APARECIO"
            )
        raise CorreccionEstablecimientoConflictError(MSG_PREVIEW_STALE, codigo="PREVIEW_STALE")

    if alta is None:
        raise CorreccionEstablecimientoError(MSG_SIN_DESTINO, codigo="SIN_DESTINO")
    fp_alta = _fingerprint_alta(scope, body.documento, alta)
    if body.fingerprint != fp_alta:
        raise CorreccionEstablecimientoConflictError(MSG_PREVIEW_STALE, codigo="PREVIEW_STALE")
    if not alta_key(alta):
        raise CorreccionEstablecimientoError(MSG_ALTA_REQUERIDA, codigo="ALTA_INCOMPLETA")

    try:
        creado = crear_contribuyente_alta(body.documento, alta)
    except DocumentoIdentidadError as exc:
        raise _wrap_documento_error(exc) from exc

    return _persistir_reasignacion(
        scope, body, actor, creado, alta=alta, creo_contribuyente=True
    )


def _persistir_reasignacion(
    scope,
    body: VinculacionEstablecimientoIn,
    actor: User,
    dest: Contribuyente,
    *,
    alta: VinculacionAltaIn | None,
    creo_contribuyente: bool,
) -> dict[str, Any]:
    """Reasigna domicilios de la ficha, audita y confirma. No hace rollback."""
    origen = scope.contribuyente
    origen_id = int(origen.id)
    dest_id = int(dest.id)
    dest_snapshot = contribuyente_publico_dict(dest)
    origen_snapshot = contribuyente_publico_dict(origen)
    otros_origen = eo_ids_contribuyente(origen_id, exclude_eo_id=int(scope.eo.id))
    otros_destino = eo_ids_contribuyente(dest_id, exclude_eo_id=int(scope.eo.id) if creo_contribuyente else None)
    canon_dest = None if creo_contribuyente else eo_canonico_destino_misma_direccion(
        scope.domicilio,
        dest,
        exclude_domicilio_ids=scope.domicilio_ids_ficha,
    )
    situacion = "ALTA" if creo_contribuyente else ("B" if canon_dest is not None else "A")
    fp = (
        _fingerprint_alta(scope, body.documento, alta)
        if creo_contribuyente and alta is not None
        else _fingerprint_existente(scope, dest, body.documento)
    )
    preview = preview_vinculacion_payload(
        scope,
        destino=dest,
        fingerprint=fp,
        situacion=situacion,
        eo_canonico_destino_id=canon_dest,
        otros_locales_origen=otros_origen,
        otros_locales_destino=otros_destino,
        puede_aplicar=True,
        puede_crear=creo_contribuyente,
        crea_contribuyente=creo_contribuyente,
    )

    for did in scope.domicilio_ids_ficha:
        dom = db.session.get(Domicilio, int(did))
        if dom is None or getattr(dom, "deleted_at", None) is not None:
            raise CorreccionEstablecimientoConflictError(MSG_PREVIEW_STALE, codigo="PREVIEW_STALE")
        if int(dom.contribuyente_id or 0) != origen_id:
            raise CorreccionEstablecimientoConflictError(MSG_PREVIEW_STALE, codigo="PREVIEW_STALE")
        dom.contribuyente_id = dest_id
        db.session.add(dom)

    db.session.flush()
    db.session.refresh(dest)
    dest_despues = contribuyente_publico_dict(dest)
    if not creo_contribuyente and dest_despues != dest_snapshot:
        raise CorreccionEstablecimientoError(
            "La vinculación no debe modificar los datos del contribuyente destino."
        )

    db.session.expire(scope.domicilio, ["contribuyente"])
    scope.domicilio.contribuyente = dest
    canon_final = eo_canonico_id_para_domicilio(scope.domicilio) or int(scope.eo.id)

    alcance = {
        "establecimiento_operativo_id": int(scope.eo.id),
        "contribuyente_origen_id": origen_id,
        "contribuyente_destino_id": dest_id,
        "domicilio_ids": scope.domicilio_ids_ficha,
        "actuacion_ids_domicilio": scope.actuacion_ids_domicilio,
        "notificacion_ids": scope.notificacion_ids,
        "comprobacion_ids": scope.comprobacion_ids,
        "oficio_ids": scope.oficio_ids,
        "iniciador_ids": scope.iniciador_ids,
        "ruta_item_ids": scope.ruta_item_ids,
        "ruta_estados_previos": scope.ruta_estados,
        "situacion": situacion,
        "ficha_logica_destino_id": canon_dest,
        "establecimiento_operativo_canonico_id": canon_final,
        "edita_datos_destino": False,
        "reescribe_actuaciones_nombre_local": False,
        "creo_contribuyente": creo_contribuyente,
    }

    audit = CorreccionEstablecimientoAudit(
        establecimiento_operativo_id=int(scope.eo.id),
        contribuyente_id=dest_id,
        domicilio_id=int(scope.domicilio.id),
        tipo="VINCULACION",
        valores_anteriores={
            "contribuyente_origen": origen_snapshot,
            "domicilio_ids": scope.domicilio_ids_ficha,
        },
        valores_nuevos={
            "contribuyente_destino": dest_snapshot,
            "domicilio_ids": scope.domicilio_ids_ficha,
            "creo_contribuyente": creo_contribuyente,
        },
        alcance=alcance,
        created_by_user_id=int(actor.id),
    )
    db.session.add(audit)
    db.session.commit()
    return apply_vinculacion_result_payload(
        preview,
        applied=True,
        audit_id=int(audit.id),
        establecimiento_operativo_canonico_id=canon_final,
    )
