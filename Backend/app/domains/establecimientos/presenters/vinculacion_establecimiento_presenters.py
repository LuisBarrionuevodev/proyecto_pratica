"""JSON de preview/resultado de vinculación de ficha a contribuyente existente."""

from __future__ import annotations

from typing import Any

from app.domains.establecimientos.mappers.correccion_establecimiento_mapper import (
    domicilio_actual_dict,
)
from app.domains.establecimientos.mappers.vinculacion_establecimiento_mapper import (
    contribuyente_publico_dict,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    CorreccionScope,
)
from app.domains.establecimientos.utils.domicilio_display import domicilio_texto_visible
from app.models import Contribuyente

ADVERTENCIA_VINCULACION = (
    "Esta operación cambia el vínculo de esta ficha al contribuyente encontrado. "
    "No edita sus datos personales. Los otros locales del contribuyente anterior y del destino "
    "no se modifican. Los PDF emitidos y los snapshots históricos no se reescriben. "
    "No se borran ni fusionan registros."
)
ADVERTENCIA_SITUACION_B = (
    "El contribuyente destino ya tiene un establecimiento en la misma dirección lógica. "
    "El listado las agrupará en la ficha canónica. No se eliminan filas físicas."
)
ADVERTENCIA_ALTA = (
    "Vas a crear a esta persona y vincular solo este establecimiento. "
    "No es un cambio de dueño a lo largo del tiempo. "
    "Los demás locales del contribuyente anterior no se modifican. "
    "Los PDF emitidos y los snapshots históricos no se reescriben. "
    "No se borran ni fusionan registros."
)


def _ids_payload(ids: list[int], *, sample: int = 20) -> dict[str, Any]:
    ordered = list(ids)
    return {"cantidad": len(ordered), "ids": ordered[:sample]}


def preview_vinculacion_payload(
    scope: CorreccionScope,
    *,
    destino: Contribuyente | None,
    fingerprint: str | None,
    situacion: str,
    eo_canonico_destino_id: int | None,
    otros_locales_origen: list[int],
    otros_locales_destino: list[int],
    puede_aplicar: bool,
    conflicto_codigo: str | None = None,
    conflicto_detail: str | None = None,
    destino_dict: dict[str, Any] | None = None,
    puede_crear: bool = False,
    crea_contribuyente: bool = False,
) -> dict[str, Any]:
    """
    Arma el resumen de alcance para confirmar la vinculación.

    Parámetros:
        scope: ficha origen comprobada.
        destino: contribuyente encontrado o None.
        fingerprint: token de preview (None si no se puede aplicar).
        situacion: A | B | BLOQUEO.
        eo_canonico_destino_id: ficha lógica destino si situación B.
        otros_locales_origen/destino: EO que no se tocan.
        puede_aplicar / conflicto_*: estado de la operación.

    Retorno:
        dict serializable.
    """
    out: dict[str, Any] = {
        "establecimiento_operativo_id": int(scope.eo.id),
        "puede_aplicar": puede_aplicar,
        "situacion": situacion,
        "fingerprint": fingerprint,
        "conflicto": None,
        "advertencias": [],
        "snapshots_y_pdf": {
            "se_actualizan": False,
            "detalle": "No se sobrescriben PDF ya emitidos ni campos titular_*_historico.",
        },
        "coordenadas_y_distrito": {
            "se_recalculan": False,
            "distrito_id": scope.domicilio.distrito_id,
            "lat": domicilio_actual_dict(scope.domicilio).get("lat"),
            "lng": domicilio_actual_dict(scope.domicilio).get("lng"),
        },
        "establecimiento": {
            "id": int(scope.eo.id),
            "domicilio_id": int(scope.domicilio.id),
            "domicilio_texto": domicilio_texto_visible(scope.domicilio),
            "domicilio_ids_ficha": scope.domicilio_ids_ficha,
            "identidad_logica_completa": scope.identity_completa,
        },
        "contribuyente_actual": contribuyente_publico_dict(scope.contribuyente),
        "contribuyente_destino": destino_dict
        if destino_dict is not None
        else contribuyente_publico_dict(destino),
        "puede_crear": puede_crear,
        "crea_contribuyente": crea_contribuyente,
        "alcance": {
            "actuaciones": _ids_payload(scope.actuacion_ids_domicilio),
            "notificaciones": _ids_payload(scope.notificacion_ids),
            "comprobaciones": _ids_payload(scope.comprobacion_ids),
            "oficios": _ids_payload(scope.oficio_ids),
            "iniciadores": _ids_payload(scope.iniciador_ids),
            "ruta_items": _ids_payload(scope.ruta_item_ids),
            "ruta_estados": scope.ruta_estados[:20],
        },
        "otros_locales_contribuyente_anterior": _ids_payload(otros_locales_origen),
        "otros_locales_contribuyente_destino": _ids_payload(otros_locales_destino),
        "ficha_logica_destino": {
            "existe": eo_canonico_destino_id is not None,
            "establecimiento_operativo_id": eo_canonico_destino_id,
        },
        "edita_datos_destino": False,
        "advertencia": ADVERTENCIA_ALTA if crea_contribuyente else ADVERTENCIA_VINCULACION,
    }
    out["advertencias"].append(out["advertencia"])
    if situacion == "B":
        out["advertencias"].append(ADVERTENCIA_SITUACION_B)
    if conflicto_codigo or conflicto_detail:
        extra_conflicto: dict[str, Any] = {
            "codigo": conflicto_codigo,
            "detail": conflicto_detail,
            "domicilio_ids_ambiguos": scope.lookalike_ids,
        }
        if puede_crear or conflicto_codigo == "SIN_DESTINO":
            extra_conflicto["puede_crear"] = True
        out["conflicto"] = extra_conflicto
        out["puede_aplicar"] = False
        if conflicto_detail:
            out["advertencias"].insert(0, conflicto_detail)
    return out


def apply_vinculacion_result_payload(
    preview: dict[str, Any],
    *,
    applied: bool,
    audit_id: int | None,
    establecimiento_operativo_canonico_id: int | None = None,
) -> dict[str, Any]:
    """Resultado de apply (mismos recuentos que el preview)."""
    return {
        **preview,
        "applied": applied,
        "audit_id": audit_id,
        "establecimiento_operativo_canonico_id": establecimiento_operativo_canonico_id,
    }
