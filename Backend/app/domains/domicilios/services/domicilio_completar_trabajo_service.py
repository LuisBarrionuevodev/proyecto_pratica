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
from app.domains.geolocalizacion.geocoding.repos.domicilio_geocode_repo import ensure_geocode_row
from app.domains.geolocalizacion.geocoding.services.geocode_orchestrator import compute_addr_hash
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

    Si el payload trae número sin calle al pasar a domicilio NUMERO, lanza error claro
    (evita mezclar calle original de esquina + número nuevo).

    Parámetros:
        payload: cierre Completar Trabajo (``calle``, ``numero``, ``numero_tipo`` opcionales).
        act: actuación en curso.
        ini: iniciador del ítem (opcional).

    Retorno:
        Dict con calle/numero/numero_tipo listo para policy y ``aplicar_edicion``.

    Errores:
        ValueError: número sin calle al corregir dirección real (ESQUINA → NUMERO).
    """
    def _norm(v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    calle_explicita = getattr(payload, "calle", None) is not None
    numero_explicito = getattr(payload, "numero", None) is not None
    numero_tipo_explicito = getattr(payload, "numero_tipo", None) is not None

    dom_payload: dict[str, Any] = {}
    if calle_explicita:
        dom_payload["calle"] = payload.calle
    if numero_explicito:
        dom_payload["numero"] = payload.numero
    if numero_tipo_explicito:
        dom_payload["numero_tipo"] = payload.numero_tipo

    if numero_explicito and not calle_explicita:
        ref_dom = act.domicilio or (ini.domicilio if ini else None)
        nt_payload = (_norm(getattr(payload, "numero_tipo", None)) or "").upper()
        nt_ref = (_norm(getattr(ref_dom, "numero_tipo", None)) or "").upper() if ref_dom else ""
        if nt_payload == "NUMERO" or nt_ref == "ESQUINA":
            raise ValueError(
                "Al corregir la dirección real (número o pasar de esquina a número), "
                "debe indicar la calle en el cierre."
            )
        raise ValueError(
            "Al corregir el domicilio en el cierre, debe indicar calle y número completos."
        )

    if calle_explicita and not numero_explicito:
        ref_dom = act.domicilio or (ini.domicilio if ini else None)
        if ref_dom is not None and ref_dom.numero:
            dom_payload["numero"] = ref_dom.numero
        else:
            raise ValueError(
                "Al corregir el domicilio en el cierre, debe indicar calle y número completos."
            )

    geo_explicito = calle_explicita or numero_explicito or numero_tipo_explicito
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

    Ajusta ``addr_hash`` al texto del domicilio nuevo y marca ``source=MANUAL`` para que
    ``on_domicilio_changed`` no dispare geocoder ni deje el registro en pending.

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
    dom_nuevo = db.session.get(Domicilio, int(domicilio_nuevo_id))
    if dom_nuevo is None:
        return
    geo = ensure_geocode_row(int(domicilio_nuevo_id))
    geo.addr_hash = compute_addr_hash(dom_nuevo)
    if geo.lat is not None and geo.lng is not None:
        geo.geo_status = snapshot.get("geo_status") or "OK"
    geo.source = "MANUAL"
    db.session.add(geo)


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
