"""
Materialización de identidad operativa en Verificar e informar → Nueva inspección.

Rama dedicada para circuito oficio: no modifica protecciones globales de
``aplicar_payload_actuacion`` ni ``_apply_domicilio_rubro``.
"""

from __future__ import annotations

from typing import Any

from app.database import db
from app.domains.actuaciones.attach.contribuyente import resolve_contribuyente
from app.domains.actuaciones.catalogs.rubro import get_rubro_o_falla
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.utils.identity_operativa_mode import (
    COMPLETE_EXISTING,
    COMPLETE_HISTORICAL,
    IdentidadAutoridad,
    identidad_autoridad_desde_origen,
)
from app.domains.domicilios.services.domicilio_completar_trabajo_service import (
    construir_cambios_domicilio_desde_payload_cierre,
    heredar_geocode_domicilio_desde_origen,
    resolver_domicilio_real_desde_completar_trabajo,
)
from app.domains.geolocalizacion.normalizacion_calles.services.normalize_domicilio_service import (
    normalizar_domicilio_en_sesion,
)
from app.domains.domicilios.utils.preservar_geocode_domicilio import (
    preservar_geocode_existente_al_editar_domicilio,
    snapshot_domicilio_geocode,
)
from app.models import Actuaciones, Domicilio, IniciadorRuta


def _clean_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _norm_cmp(v: Any) -> str:
    return (_clean_str(v) or "").casefold()


def validar_tampering_identidad_existente(
    payload: CompletarTrabajoCierreCompletoIn,
    authority: IdentidadAutoridad,
) -> None:
    """
    Rechaza payload con identidad distinta a la autorizada del origen.

    Parámetros:
        payload: body del cierre.
        authority: identidad resuelta desde actuación origen.

    Errores:
        ValueError: si algún campo enviado contradice la autoridad.
    """
    checks = (
        ("doc_nro", payload.doc_nro, authority.get("doc_nro")),
        ("contrib_apellido", payload.contrib_apellido, authority.get("contrib_apellido")),
        ("contrib_nombre", payload.contrib_nombre, authority.get("contrib_nombre")),
        ("razon_social", payload.razon_social, authority.get("razon_social")),
        ("rubro_nombre", payload.rubro_nombre, authority.get("rubro_nombre")),
    )
    for label, sent, allowed in checks:
        if _norm_cmp(sent) and _norm_cmp(allowed) and _norm_cmp(sent) != _norm_cmp(allowed):
            raise ValueError(
                f"La identidad enviada en {label!r} no coincide con la actuación origen."
            )


def _validar_titular_historico_payload(payload: CompletarTrabajoCierreCompletoIn) -> None:
    """Exige titular + documento + rubro según contrato normal."""
    has_persona = bool(_clean_str(payload.contrib_apellido) and _clean_str(payload.contrib_nombre))
    has_razon = bool(_clean_str(payload.razon_social))
    if has_persona and has_razon:
        raise ValueError("Ingrese nombre y apellido o razón social, no ambos.")
    if not has_persona and not has_razon:
        raise ValueError("Ingrese nombre y apellido o razón social.")
    if not _clean_str(payload.doc_nro):
        raise ValueError("Documento del contribuyente es obligatorio.")
    if not _clean_str(payload.rubro_nombre):
        raise ValueError("Rubro es obligatorio.")


def _vincular_domicilio_operativo(
    act: Actuaciones,
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
    *,
    contrib,
    rubro,
) -> Domicilio:
    """
    Resuelve domicilio de trabajo con COW cuando corresponde.

    Parámetros:
        act: actuación de ruta.
        ini: iniciador.
        payload: cierre con calle/número opcionales.
        contrib: contribuyente formal resuelto.
        rubro: rubro resuelto.

    Retorno:
        Domicilio operativo vinculado a la actuación de trabajo.
    """
    dom_payload = construir_cambios_domicilio_desde_payload_cierre(payload, act=act, ini=ini)
    domicilio_id_ref = act.domicilio_id or (ini.domicilio_id if ini else None)
    geo_snapshot = (
        snapshot_domicilio_geocode(int(domicilio_id_ref))
        if domicilio_id_ref is not None
        else None
    )
    outcome = resolver_domicilio_real_desde_completar_trabajo(
        domicilio_origen_id=domicilio_id_ref,
        payload_cambios=dom_payload,
        contribuyente=contrib,
        rubro=rubro,
        act_id=int(act.id),
        relevamiento_id=None,
        modo_explicito=getattr(payload, "modo_domicilio", None),
        allow_missing_catalogs=False,
    )
    dom = outcome.domicilio
    if dom is None:
        raise ValueError("No se pudo resolver el domicilio operativo.")
    act.domicilio_id = dom.id
    act.domicilio = dom
    normalizar_domicilio_en_sesion(dom, override_numero_tipo=dom_payload.get("numero_tipo"))
    if outcome.domicilio_id_cambio and domicilio_id_ref is not None:
        heredar_geocode_domicilio_desde_origen(int(domicilio_id_ref), int(dom.id))
    elif geo_snapshot is not None and not outcome.domicilio_id_cambio:
        preservar_geocode_existente_al_editar_domicilio(int(dom.id), geo_snapshot)
    if ini.domicilio_id != act.domicilio_id:
        ini.domicilio_id = act.domicilio_id
    db.session.add(act)
    db.session.add(ini)
    db.session.add(dom)
    return dom


def completar_identidad_operativa_verificar_informar(
    act: Actuaciones,
    ini: IniciadorRuta,
    payload: CompletarTrabajoCierreCompletoIn,
    *,
    identity_mode: str,
) -> None:
    """
    Materializa o preserva identidad operativa en cierre Verificar+Nueva inspección.

    Parámetros:
        act: actuación de trabajo (ruta).
        ini: iniciador del ítem.
        payload: body validado del cierre.
        identity_mode: ``COMPLETE_HISTORICAL`` o ``COMPLETE_EXISTING``.

    Errores:
        ValueError: validación de titular/documento/rubro o tampering.
    """
    if identity_mode == COMPLETE_HISTORICAL:
        _validar_titular_historico_payload(payload)
        contrib = resolve_contribuyente(
            {
                "doc_nro": _clean_str(payload.doc_nro),
                "apellido": _clean_str(payload.contrib_apellido),
                "nombre": _clean_str(payload.contrib_nombre),
                "razon_social": _clean_str(payload.razon_social),
            }
        )
        rubro = get_rubro_o_falla(_clean_str(payload.rubro_nombre))
        _vincular_domicilio_operativo(act, ini, payload, contrib=contrib, rubro=rubro)
        return

    if identity_mode == COMPLETE_EXISTING:
        authority = identidad_autoridad_desde_origen(ini, act_trabajo=act)
        validar_tampering_identidad_existente(payload, authority)
        contrib = resolve_contribuyente(
            {
                "doc_nro": authority["doc_nro"],
                "apellido": authority.get("contrib_apellido"),
                "nombre": authority.get("contrib_nombre"),
                "razon_social": authority.get("razon_social"),
            }
        )
        rubro = get_rubro_o_falla(authority["rubro_nombre"])
        _vincular_domicilio_operativo(act, ini, payload, contrib=contrib, rubro=rubro)
        return

    raise ValueError(f"Modo de identidad no soportado: {identity_mode!r}.")
