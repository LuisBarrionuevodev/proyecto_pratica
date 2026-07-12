"""
Copy-on-write de domicilio real/legal al completar trabajo desde relevamiento (PR7.12).
"""

from __future__ import annotations

from typing import Any

from app.database import db
from app.models import Actuaciones, Domicilio, IniciadorRuta, RutaItem
from app.domains.domicilios.services.domicilio_update_service import (
    AplicarDomicilioOutcome,
    aplicar_edicion_domicilio_operativo,
)
from app.domains.domicilios.utils.preservar_geocode_domicilio import (
    preservar_geocode_existente_al_editar_domicilio,
    restaurar_domicilio_geocode_desde_snapshot,
    snapshot_domicilio_geocode,
)


def relevamiento_id_desde_actuacion(actuacion_id: int) -> int | None:
    """
    Obtiene ``relevamiento_id`` del iniciador vinculado a la actuación vía ``RutaItem``.

    Parámetros:
        actuacion_id: id de la actuación.

    Retorno:
        ``relevamiento_id`` si el ítem de ruta proviene de relevamiento; si no, ``None``.
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(actuacion_id),
            RutaItem.deleted_at.is_(None),
        )
        .first()
    )
    if item is None:
        return None
    ini = db.session.get(IniciadorRuta, int(item.iniciador_ruta_id))
    if ini is None or ini.deleted_at is not None or ini.relevamiento_id is None:
        return None
    return int(ini.relevamiento_id)


def construir_cambios_domicilio_desde_payload_cierre(
    payload: Any,
    *,
    act: Actuaciones,
    ini: IniciadorRuta | None,
) -> dict[str, Any]:
    """
    Arma el dict de cambios de domicilio usando solo campos explícitos del payload.

    Solo rellena calle/número desde el domicilio actual si no hubo ningún campo geográfico
    en el cierre (p. ej. actualización de rubro/contrib sin cambio de dirección).

    Parámetros:
        payload: cierre Completar Trabajo (``calle``, ``numero``, ``numero_tipo`` opcionales).
        act: actuación en curso.
        ini: iniciador del ítem (opcional).

    Retorno:
        Dict con calle/numero/numero_tipo listo para policy y ``aplicar_edicion``.
    """
    dom_payload: dict[str, Any] = {}
    if getattr(payload, "calle", None) is not None:
        dom_payload["calle"] = payload.calle
    if getattr(payload, "numero", None) is not None:
        dom_payload["numero"] = payload.numero
    if getattr(payload, "numero_tipo", None) is not None:
        dom_payload["numero_tipo"] = payload.numero_tipo

    geo_explicito = bool(dom_payload)
    if not geo_explicito:
        ref_dom = act.domicilio or (ini.domicilio if ini else None)
        if ref_dom is not None:
            dom_payload["calle"] = ref_dom.calle
            dom_payload["numero"] = ref_dom.numero
            if ref_dom.numero_tipo:
                dom_payload["numero_tipo"] = ref_dom.numero_tipo

    return dom_payload


def heredar_geocode_domicilio_desde_origen(
    domicilio_origen_id: int,
    domicilio_nuevo_id: int,
) -> None:
    """
    Copia lat/lng y metadatos de geocode del domicilio origen al nuevo domicilio real.

    No dispara geocoder ni marca pending: conserva el geocode heredado del relevamiento.

    Parámetros:
        domicilio_origen_id: domicilio histórico del relevamiento/iniciador.
        domicilio_nuevo_id: domicilio real/legal creado en Completar Trabajo.

    Retorno:
        None (sin commit).
    """
    snapshot = snapshot_domicilio_geocode(int(domicilio_origen_id))
    if not snapshot:
        return
    restaurar_domicilio_geocode_desde_snapshot(int(domicilio_nuevo_id), snapshot)


def resolver_domicilio_real_desde_completar_trabajo(
    *,
    domicilio_origen_id: int | None,
    payload_cambios: dict[str, Any],
    contribuyente: Any,
    rubro: Any,
    act_id: int,
    relevamiento_id: int | None,
    modo_explicito: str | None = None,
    allow_missing_catalogs: bool = False,
) -> AplicarDomicilioOutcome:
    """
    Resuelve o crea el domicilio real/legal para Completar Trabajo con copy-on-write desde relevamiento.

    Si ``relevamiento_id`` está presente y el payload cambia texto geográfico, la policy crea una
    fila nueva en lugar de mutar el domicilio compartido del relevamiento. El geocode del origen
    se hereda al domicilio nuevo.

    Parámetros:
        domicilio_origen_id: FK domicilio actual (actuación/iniciador).
        payload_cambios: calle, numero, numero_tipo explícitos del cierre.
        contribuyente/rubro: catálogos para get-or-create.
        act_id: id de la actuación (policy).
        relevamiento_id: id del relevamiento origen; habilita copy-on-write.
        modo_explicito: intención del frontend (NUEVO / REASIGNAR).
        allow_missing_catalogs: permite domicilio sin rubro/contrib en visita no realizada.

    Retorno:
        ``AplicarDomicilioOutcome`` con domicilio resultante.

    Errores:
        ValueError: policy BLOQUEAR o datos insuficientes.
    """
    geo_snapshot = (
        snapshot_domicilio_geocode(int(domicilio_origen_id))
        if domicilio_origen_id is not None
        else None
    )
    outcome = aplicar_edicion_domicilio_operativo(
        domicilio_id_actual=domicilio_origen_id,
        cambios=payload_cambios,
        contribuyente=contribuyente,
        rubro=rubro,
        contexto="COMPLETAR_TRABAJO",
        origen_id=int(act_id),
        modo_explicito=modo_explicito,
        allow_missing_catalogs=allow_missing_catalogs,
        relevamiento_id=relevamiento_id,
    )
    dom = outcome.domicilio
    if dom is None:
        return outcome

    if outcome.domicilio_id_cambio and domicilio_origen_id is not None:
        heredar_geocode_domicilio_desde_origen(int(domicilio_origen_id), int(dom.id))
    elif (
        outcome.policy.modo == "EDITAR_MISMA_FILA"
        and not outcome.domicilio_id_cambio
        and geo_snapshot is not None
    ):
        preservar_geocode_existente_al_editar_domicilio(int(dom.id), geo_snapshot)

    return outcome
