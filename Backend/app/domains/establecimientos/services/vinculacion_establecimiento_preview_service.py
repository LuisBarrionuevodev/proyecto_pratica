"""Vista previa de vinculación (solo lectura, sin persistir)."""

from __future__ import annotations

from typing import Any

from app.domains.establecimientos.mappers.vinculacion_establecimiento_mapper import (
    fingerprint_vinculacion,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_alta import (
    alta_desde_body,
    alta_key,
    destino_propuesto_dict,
    documento_norm_body,
)
from app.domains.establecimientos.presenters.vinculacion_establecimiento_presenters import (
    preview_vinculacion_payload,
)
from app.domains.establecimientos.schemas.vinculacion_establecimiento_in import (
    VinculacionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_AMBIGUEDAD,
    MSG_SIN_CONTRIB,
    assert_rol_puede_corregir,
    cargar_ficha_para_correccion,
)
from app.domains.establecimientos.services.vinculacion_establecimiento_resolver import (
    MSG_IDENTIDAD_INCOMPLETA,
    eo_canonico_destino_misma_direccion,
    eo_ids_contribuyente,
    lookalike_ids_destino,
    resolver_contribuyente_destino,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
)
from app.models import User


def preview_vinculacion_establecimiento(
    establecimiento_id: int,
    body: VinculacionEstablecimientoIn,
    *,
    actor: User,
) -> dict[str, Any]:
    """
    Calcula destino y alcance de una vinculación sin escribir.

    Parámetros:
        establecimiento_id: ficha abierta.
        body: documento ingresado.
        actor: usuario JWT (admin/usuario).

    Retorno:
        Preview con puede_aplicar, situacion A/B/BLOQUEO y fingerprint.

    Errores:
        403/404 permiso o ficha inexistente.
        Conflictos de lookup se devuelven en el payload (no 409) para que la UI explique.
    """
    assert_rol_puede_corregir(actor)
    scope = cargar_ficha_para_correccion(establecimiento_id, for_update=False)
    if scope.contribuyente is None:
        return preview_vinculacion_payload(
            scope,
            destino=None,
            fingerprint=None,
            situacion="BLOQUEO",
            eo_canonico_destino_id=None,
            otros_locales_origen=[],
            otros_locales_destino=[],
            puede_aplicar=False,
            conflicto_codigo="SIN_CONTRIBUYENTE",
            conflicto_detail=MSG_SIN_CONTRIB,
        )

    if not scope.identity_completa:
        return preview_vinculacion_payload(
            scope,
            destino=None,
            fingerprint=None,
            situacion="BLOQUEO",
            eo_canonico_destino_id=None,
            otros_locales_origen=eo_ids_contribuyente(
                int(scope.contribuyente.id), exclude_eo_id=int(scope.eo.id)
            ),
            otros_locales_destino=[],
            puede_aplicar=False,
            conflicto_codigo="IDENTIDAD_INCOMPLETA",
            conflicto_detail=MSG_IDENTIDAD_INCOMPLETA,
        )

    if scope.lookalike_ids:
        return preview_vinculacion_payload(
            scope,
            destino=None,
            fingerprint=None,
            situacion="BLOQUEO",
            eo_canonico_destino_id=None,
            otros_locales_origen=eo_ids_contribuyente(
                int(scope.contribuyente.id), exclude_eo_id=int(scope.eo.id)
            ),
            otros_locales_destino=[],
            puede_aplicar=False,
            conflicto_codigo="AMBIGUEDAD_DOMICILIO",
            conflicto_detail=MSG_AMBIGUEDAD,
        )

    try:
        dest = resolver_contribuyente_destino(body.documento, scope.contribuyente)
    except (CorreccionEstablecimientoConflictError, CorreccionEstablecimientoError) as exc:
        codigo = getattr(exc, "codigo", None)
        otros_origen = eo_ids_contribuyente(
            int(scope.contribuyente.id), exclude_eo_id=int(scope.eo.id)
        )
        if codigo == "SIN_DESTINO":
            alta = alta_desde_body(body)
            if alta is None:
                return preview_vinculacion_payload(
                    scope,
                    destino=None,
                    fingerprint=None,
                    situacion="BLOQUEO",
                    eo_canonico_destino_id=None,
                    otros_locales_origen=otros_origen,
                    otros_locales_destino=[],
                    puede_aplicar=False,
                    conflicto_codigo="SIN_DESTINO",
                    conflicto_detail=exc.detail,
                    puede_crear=True,
                )
            fp = fingerprint_vinculacion(
                establecimiento_id=int(scope.eo.id),
                origen_id=int(scope.contribuyente.id),
                destino_id=0,
                domicilio_ids=scope.domicilio_ids_ficha,
                lookalike_ids=scope.lookalike_ids,
                modo="ALTA",
                documento_norm=documento_norm_body(body.documento),
                alta_key=alta_key(alta),
            )
            return preview_vinculacion_payload(
                scope,
                destino=None,
                fingerprint=fp,
                situacion="ALTA",
                eo_canonico_destino_id=None,
                otros_locales_origen=otros_origen,
                otros_locales_destino=[],
                puede_aplicar=True,
                destino_dict=destino_propuesto_dict(body.documento, alta),
                puede_crear=True,
                crea_contribuyente=True,
            )
        return preview_vinculacion_payload(
            scope,
            destino=None,
            fingerprint=None,
            situacion="BLOQUEO",
            eo_canonico_destino_id=None,
            otros_locales_origen=otros_origen,
            otros_locales_destino=[],
            puede_aplicar=False,
            conflicto_codigo=codigo,
            conflicto_detail=exc.detail,
        )

    dest_look = lookalike_ids_destino(
        scope.domicilio,
        dest,
        exclude_domicilio_ids=scope.domicilio_ids_ficha,
    )
    if dest_look:
        return preview_vinculacion_payload(
            scope,
            destino=dest,
            fingerprint=None,
            situacion="BLOQUEO",
            eo_canonico_destino_id=None,
            otros_locales_origen=eo_ids_contribuyente(
                int(scope.contribuyente.id), exclude_eo_id=int(scope.eo.id)
            ),
            otros_locales_destino=eo_ids_contribuyente(int(dest.id)),
            puede_aplicar=False,
            conflicto_codigo="AMBIGUEDAD_DOMICILIO",
            conflicto_detail=MSG_AMBIGUEDAD,
        )

    canon_dest = eo_canonico_destino_misma_direccion(
        scope.domicilio,
        dest,
        exclude_domicilio_ids=scope.domicilio_ids_ficha,
    )
    situacion = "B" if canon_dest is not None else "A"
    fp = fingerprint_vinculacion(
        establecimiento_id=int(scope.eo.id),
        origen_id=int(scope.contribuyente.id),
        destino_id=int(dest.id),
        domicilio_ids=scope.domicilio_ids_ficha,
        lookalike_ids=scope.lookalike_ids,
        modo="EXISTENTE",
        documento_norm=documento_norm_body(body.documento),
    )
    return preview_vinculacion_payload(
        scope,
        destino=dest,
        fingerprint=fp,
        situacion=situacion,
        eo_canonico_destino_id=canon_dest,
        otros_locales_origen=eo_ids_contribuyente(
            int(scope.contribuyente.id), exclude_eo_id=int(scope.eo.id)
        ),
        otros_locales_destino=eo_ids_contribuyente(int(dest.id)),
        puede_aplicar=True,
    )
