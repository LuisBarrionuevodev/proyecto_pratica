"""Preview del alcance de una corrección controlada (sin persistir)."""

from __future__ import annotations

from typing import Any

from app.domains.establecimientos.mappers.correccion_establecimiento_mapper import (
    hay_cambio_contribuyente,
    hay_cambio_domicilio,
    hay_cambio_local,
    proposicion_contribuyente,
    proposicion_domicilio,
    proposicion_local,
    contribuyente_actual_dict,
    domicilio_actual_dict,
    local_actual_dict,
)
from app.domains.establecimientos.presenters.correccion_establecimiento_presenters import (
    preview_correccion_payload,
)
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_SIN_CONTRIB,
    assert_rol_puede_corregir,
    cargar_ficha_para_correccion,
    validar_documento_propuesto,
    validar_no_fusion_identidad,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
)
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.models import User


def preview_correccion_establecimiento(
    establecimiento_id: int,
    body: CorreccionEstablecimientoIn,
    *,
    actor: User,
) -> dict[str, Any]:
    """
    Calcula el resumen de impacto antes de guardar.

    Parámetros:
        establecimiento_id: ficha seleccionada.
        body: payload validado (contribuyente y/o domicilio).
        actor: usuario autenticado (permiso admin/usuario).

    Retorno:
        dict serializable con actual/propuesto, cantidades y advertencias.

    Errores:
        CorreccionEstablecimientoPermisoError / NotFoundError / Error de validación.
        Conflictos de documento o fusión se informan en el payload (puede_aplicar=false)
        salvo documento ajeno, que se expone también como 409 en apply.
    """
    assert_rol_puede_corregir(actor)
    scope = cargar_ficha_para_correccion(establecimiento_id, for_update=False)

    incluir_contrib = body.contribuyente is not None
    incluir_dom = body.domicilio is not None
    incluir_local = body.local is not None

    propuesto_c = None
    cambia_c = False
    if incluir_contrib:
        if scope.contribuyente is None:
            raise CorreccionEstablecimientoError(MSG_SIN_CONTRIB)
        propuesto_c = proposicion_contribuyente(scope.contribuyente, body.contribuyente)
        actual_c = contribuyente_actual_dict(scope.contribuyente) or {}
        cambia_c = hay_cambio_contribuyente(actual_c, propuesto_c)
        if cambia_c:
            try:
                validar_documento_propuesto(scope.contribuyente, str(propuesto_c.get("documento") or ""))
            except CorreccionEstablecimientoConflictError as exc:
                payload = preview_correccion_payload(
                    scope,
                    propuesto_contrib=propuesto_c,
                    propuesto_dom=None,
                    cambia_contrib=cambia_c,
                    cambia_dom=False,
                    incluir_contrib=True,
                    incluir_dom=incluir_dom,
                )
                payload["puede_aplicar"] = False
                payload["conflicto"] = {"codigo": exc.codigo, "detail": exc.detail}
                payload["advertencias"] = [exc.detail, *payload.get("advertencias", [])]
                return payload

    propuesto_d = None
    cambia_d = False
    if incluir_dom:
        propuesto_d = proposicion_domicilio(scope.domicilio, body.domicilio)
        actual_d = domicilio_actual_dict(scope.domicilio)
        cambia_d = hay_cambio_domicilio(actual_d, propuesto_d)
        if not (propuesto_d.get("calle") or "").strip() or not (propuesto_d.get("numero") or "").strip():
            raise CorreccionEstablecimientoError("Calle y número/intersección son obligatorios.")
        if cambia_d:
            try:
                validar_no_fusion_identidad(
                    scope.domicilio,
                    scope.contribuyente,
                    calle=str(propuesto_d["calle"]),
                    numero=str(propuesto_d["numero"]),
                    numero_tipo=propuesto_d.get("numero_tipo"),
                    esquina=propuesto_d.get("esquina"),
                    scope_ids=scope.domicilio_ids_ficha,
                )
            except CorreccionEstablecimientoConflictError as exc:
                payload = preview_correccion_payload(
                    scope,
                    propuesto_contrib=propuesto_c,
                    propuesto_dom=propuesto_d,
                    cambia_contrib=cambia_c,
                    cambia_dom=cambia_d,
                    incluir_contrib=incluir_contrib,
                    incluir_dom=True,
                )
                payload["puede_aplicar"] = False
                payload["conflicto"] = {"codigo": exc.codigo, "detail": exc.detail}
                payload["advertencias"] = [exc.detail, *payload.get("advertencias", [])]
                return payload

    propuesto_l = None
    cambia_l = False
    if incluir_local:
        actual_l = local_actual_dict(scope.eo)
        propuesto_l = proposicion_local(actual_l, body.local)
        cambia_l = hay_cambio_local(actual_l, propuesto_l)
        rubro_nombre = propuesto_l.get("rubro_nombre")
        if rubro_nombre:
            try:
                get_rubro_o_falla(str(rubro_nombre))
            except ValueError as exc:
                raise CorreccionEstablecimientoError(str(exc)) from exc

    return preview_correccion_payload(
        scope,
        propuesto_contrib=propuesto_c,
        propuesto_dom=propuesto_d,
        propuesto_local=propuesto_l,
        cambia_contrib=cambia_c,
        cambia_dom=cambia_d,
        cambia_local=cambia_l,
        incluir_contrib=incluir_contrib,
        incluir_dom=incluir_dom,
        incluir_local=incluir_local,
    )
