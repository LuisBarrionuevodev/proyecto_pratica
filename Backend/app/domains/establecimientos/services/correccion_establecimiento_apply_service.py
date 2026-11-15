"""Aplicación atómica de corrección controlada desde la ficha."""

from __future__ import annotations

from typing import Any

from app.database import db
from app.domains.domicilios.utils.preservar_geocode_domicilio import (
    preservar_geocode_existente_al_editar_domicilio,
    snapshot_domicilio_geocode,
)
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.establecimientos.mappers.correccion_establecimiento_mapper import (
    contribuyente_actual_dict,
    domicilio_actual_dict,
    hay_cambio_contribuyente,
    hay_cambio_domicilio,
    hay_cambio_local,
    local_actual_dict,
    proposicion_contribuyente,
    proposicion_domicilio,
    proposicion_local,
)
from app.domains.establecimientos.presenters.correccion_establecimiento_presenters import (
    apply_result_payload,
    preview_correccion_payload,
)
from app.domains.establecimientos.schemas.correccion_establecimiento_in import (
    CorreccionEstablecimientoIn,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    MSG_AMBIGUEDAD,
    MSG_SIN_CONTRIB,
    CorreccionScope,
    assert_rol_puede_corregir,
    cargar_ficha_para_correccion,
    validar_documento_propuesto,
    validar_no_fusion_identidad,
)
from app.domains.establecimientos.utils.correccion_establecimiento_errors import (
    CorreccionEstablecimientoConflictError,
    CorreccionEstablecimientoError,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.models import CorreccionEstablecimientoAudit, Domicilio, User


def aplicar_correccion_establecimiento(
    establecimiento_id: int,
    body: CorreccionEstablecimientoIn,
    *,
    actor: User,
) -> dict[str, Any]:
    """
    Aplica la corrección en una sola transacción y registra auditoría.

    Parámetros:
        establecimiento_id: ficha seleccionada.
        body: payload validado; ``confirmado`` debe ser True.
        actor: usuario JWT (admin/usuario).

    Retorno:
        dict con applied, audit_id y el mismo alcance que el preview.

    Errores:
        400 si falta confirmación o validación de negocio.
        409 documento ajeno, ambigüedad de domicilio o fusión de ficha.
        403/404 según permiso o ficha inexistente.
        Rollback si cualquier paso falla (sin corrección parcial).
    """
    assert_rol_puede_corregir(actor)
    if body.confirmado is not True:
        raise CorreccionEstablecimientoError(
            "Debe confirmar explícitamente la corrección antes de guardar."
        )

    try:
        return _aplicar_en_transaccion(establecimiento_id, body, actor)
    except Exception:
        db.session.rollback()
        raise


def _aplicar_en_transaccion(
    establecimiento_id: int,
    body: CorreccionEstablecimientoIn,
    actor: User,
) -> dict[str, Any]:
    scope = cargar_ficha_para_correccion(establecimiento_id, for_update=True)

    incluir_contrib = body.contribuyente is not None
    incluir_dom = body.domicilio is not None
    incluir_local = body.local is not None
    if incluir_dom and scope.lookalike_ids:
        raise CorreccionEstablecimientoConflictError(MSG_AMBIGUEDAD, codigo="AMBIGUEDAD_DOMICILIO")

    propuesto_c = None
    cambia_c = False
    if incluir_contrib:
        if scope.contribuyente is None:
            raise CorreccionEstablecimientoError(MSG_SIN_CONTRIB)
        propuesto_c = proposicion_contribuyente(scope.contribuyente, body.contribuyente)
        actual_c = contribuyente_actual_dict(scope.contribuyente) or {}
        cambia_c = hay_cambio_contribuyente(actual_c, propuesto_c)
        if cambia_c:
            validar_documento_propuesto(scope.contribuyente, str(propuesto_c.get("documento") or ""))

    propuesto_d = None
    cambia_d = False
    if incluir_dom:
        propuesto_d = proposicion_domicilio(scope.domicilio, body.domicilio)
        actual_d = domicilio_actual_dict(scope.domicilio)
        cambia_d = hay_cambio_domicilio(actual_d, propuesto_d)
        if not (propuesto_d.get("calle") or "").strip() or not (propuesto_d.get("numero") or "").strip():
            raise CorreccionEstablecimientoError("Calle y número/intersección son obligatorios.")
        if cambia_d:
            validar_no_fusion_identidad(
                scope.domicilio,
                scope.contribuyente,
                calle=str(propuesto_d["calle"]),
                numero=str(propuesto_d["numero"]),
                numero_tipo=propuesto_d.get("numero_tipo"),
                esquina=propuesto_d.get("esquina"),
                scope_ids=scope.domicilio_ids_ficha,
            )

    propuesto_l = None
    cambia_l = False
    rubro_obj = None
    if incluir_local:
        actual_l = local_actual_dict(scope.eo)
        propuesto_l = proposicion_local(actual_l, body.local)
        cambia_l = hay_cambio_local(actual_l, propuesto_l)
        rubro_nombre = propuesto_l.get("rubro_nombre") if propuesto_l else None
        if rubro_nombre:
            try:
                rubro_obj = get_rubro_o_falla(str(rubro_nombre))
            except ValueError as exc:
                raise CorreccionEstablecimientoError(str(exc)) from exc

    preview = preview_correccion_payload(
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

    if not cambia_c and not cambia_d and not cambia_l:
        return apply_result_payload(preview, applied=False, audit_id=None)

    valores_anteriores: dict[str, Any] = {}
    valores_nuevos: dict[str, Any] = {}

    if cambia_c and scope.contribuyente is not None and propuesto_c is not None:
        valores_anteriores["contribuyente"] = contribuyente_actual_dict(scope.contribuyente)
        contrib = scope.contribuyente
        contrib.documento = str(propuesto_c["documento"])
        contrib.apellido = propuesto_c.get("apellido")
        contrib.nombre = propuesto_c.get("nombre")
        contrib.razon_social = propuesto_c.get("razon_social")
        db.session.add(contrib)
        valores_nuevos["contribuyente"] = {
            "id": int(contrib.id),
            **propuesto_c,
        }

    if cambia_d and propuesto_d is not None:
        valores_anteriores["domicilios"] = [
            domicilio_actual_dict(db.session.get(Domicilio, did) or scope.domicilio)
            for did in scope.domicilio_ids_ficha
        ]
        _corregir_domicilios_ficha(scope.domicilio_ids_ficha, propuesto_d)
        valores_nuevos["domicilios"] = [
            {
                "id": did,
                "calle": propuesto_d.get("calle"),
                "numero": propuesto_d.get("numero"),
                "numero_tipo": propuesto_d.get("numero_tipo"),
                "esquina": propuesto_d.get("esquina"),
            }
            for did in scope.domicilio_ids_ficha
        ]

    if cambia_l and not cambia_c and not cambia_d:
        tipo = "LOCAL"
        valores_anteriores["local"] = local_actual_dict(scope.eo)
        _aplicar_local_ficha(scope, propuesto_l or {}, rubro_obj)
        rubro_id_nuevo = (
            int(rubro_obj.id)
            if rubro_obj is not None
            else (int(scope.domicilio.rubro_id) if scope.domicilio.rubro_id is not None else None)
        )
        valores_nuevos["local"] = {
            "establecimiento_operativo_id": int(scope.eo.id),
            "domicilio_id": int(scope.domicilio.id),
            **(propuesto_l or {}),
            "rubro_id": rubro_id_nuevo,
        }
    elif cambia_c and cambia_d:
        tipo = "AMBOS"
    elif cambia_c:
        tipo = "CONTRIBUYENTE"
    else:
        tipo = "DOMICILIO"

    alcance = {
        "establecimiento_operativo_id": int(scope.eo.id),
        "contribuyente_id": int(scope.contribuyente.id) if scope.contribuyente else None,
        "domicilio_ids": scope.domicilio_ids_ficha if cambia_d else [int(scope.domicilio.id)],
        "establecimiento_ids_contribuyente": scope.establecimiento_ids_contribuyente if cambia_c else [],
        "actuacion_ids_contribuyente": scope.actuacion_ids_contribuyente if cambia_c else [],
        "actuacion_ids_domicilio": scope.actuacion_ids_domicilio if (cambia_d or cambia_l) else [],
        "notificacion_ids": scope.notificacion_ids if cambia_d else [],
        "comprobacion_ids": scope.comprobacion_ids if cambia_d else [],
        "oficio_ids": scope.oficio_ids if cambia_d else [],
        "iniciador_ids": scope.iniciador_ids if cambia_d else [],
        "ruta_item_ids": scope.ruta_item_ids if cambia_d else [],
        "ruta_estados_previos": scope.ruta_estados if cambia_d else [],
        "reescribe_actuaciones_nombre_local": False,
    }

    audit = CorreccionEstablecimientoAudit(
        establecimiento_operativo_id=int(scope.eo.id),
        contribuyente_id=int(scope.contribuyente.id) if scope.contribuyente else None,
        domicilio_id=int(scope.domicilio.id),
        tipo=tipo,
        valores_anteriores=valores_anteriores,
        valores_nuevos=valores_nuevos,
        alcance=alcance,
        created_by_user_id=int(actor.id),
    )
    db.session.add(audit)
    db.session.commit()
    return apply_result_payload(preview, applied=True, audit_id=int(audit.id))


def _aplicar_local_ficha(
    scope: CorreccionScope,
    propuesto: dict[str, Any],
    rubro_obj: Any,
) -> None:
    """
    Actualiza rubro del domicilio ancla y nombre_local de esta ficha.

    No toca otros establecimientos del contribuyente ni reescribe actuaciones.
    Conserva contribuyente_id, geocode, distrito y barrio.
    """
    dom = scope.domicilio
    distrito_id = dom.distrito_id
    barrio_id = dom.barrio_id
    contribuyente_id = dom.contribuyente_id
    if rubro_obj is not None:
        dom.rubro_id = int(rubro_obj.id)
    if "nombre_local" in propuesto:
        raw = propuesto.get("nombre_local")
        scope.eo.nombre_local = (str(raw).strip() or None) if raw is not None else scope.eo.nombre_local
    dom.distrito_id = distrito_id
    dom.barrio_id = barrio_id
    dom.contribuyente_id = contribuyente_id
    db.session.add(dom)
    db.session.add(scope.eo)
    db.session.flush()


def _corregir_domicilios_ficha(domicilio_ids: list[int], propuesto: dict[str, Any]) -> None:
    """
    Actualiza in-place las filas físicas comprobadas de la ficha.

    Conserva distrito/barrio y restaura geocode (sin on_domicilio_changed).
    """
    calle = str(propuesto["calle"]).strip()
    numero = str(propuesto["numero"]).strip()
    numero_tipo = propuesto.get("numero_tipo")
    esquina = propuesto.get("esquina")
    nt = (numero_tipo or "").strip().upper() or None
    if nt == "ESQUINA" and esquina:
        numero = str(esquina).strip()

    for did in domicilio_ids:
        dom = db.session.get(Domicilio, int(did))
        if dom is None or getattr(dom, "deleted_at", None) is not None:
            raise CorreccionEstablecimientoError(
                "Un domicilio del alcance dejó de estar disponible. No se aplicó la corrección."
            )
        geo_snap = snapshot_domicilio_geocode(int(dom.id))
        distrito_id = dom.distrito_id
        barrio_id = dom.barrio_id
        contribuyente_id = dom.contribuyente_id
        rubro_id = dom.rubro_id

        dom.calle = calle
        dom.numero = numero
        if nt:
            dom.numero_tipo = nt
        db.session.add(dom)
        db.session.flush()
        normalizar_domicilio_en_sesion(dom, override_numero_tipo=nt)
        dom.distrito_id = distrito_id
        dom.barrio_id = barrio_id
        dom.contribuyente_id = contribuyente_id
        dom.rubro_id = rubro_id
        db.session.add(dom)
        db.session.flush()
        preservar_geocode_existente_al_editar_domicilio(int(dom.id), geo_snap)
