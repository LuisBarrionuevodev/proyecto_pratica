"""JSON de preview/resultado de corrección controlada desde la ficha."""

from __future__ import annotations

from typing import Any

from app.domains.establecimientos.mappers.correccion_establecimiento_mapper import (
    contribuyente_actual_dict,
    domicilio_actual_dict,
    local_actual_dict,
)
from app.domains.establecimientos.services.correccion_establecimiento_scope_service import (
    CorreccionScope,
)
from app.domains.establecimientos.utils.domicilio_display import domicilio_texto_visible


ADVERTENCIA_CONTRIBUYENTE = (
    "La corrección se reflejará en todos los establecimientos asociados a este contribuyente. "
    "No cambia el titular ni fusiona registros. "
    "Los PDF ya emitidos y los snapshots históricos (titular_*_historico) no se actualizan."
)
ADVERTENCIA_DOMICILIO = (
    "Se corrige el domicilio de origen de esta ficha y las vistas en vivo que lo leen "
    "(actuaciones, notificaciones, comprobaciones, oficios, iniciadores e ítems de ruta vinculados). "
    "Las coordenadas y el distrito no se recalcularán automáticamente; podrían no coincidir "
    "con la dirección corregida. No se modifican estados, rutas, actas ni archivos ya emitidos. "
    "Los PDF descargados y snapshots históricos no cambian."
)
ADVERTENCIA_SIN_CAMBIOS = "No hay cambios para aplicar. No se desvincula el contribuyente ni se modifica ningún dato."
ADVERTENCIA_LOCAL = (
    "Se corrigen el rubro y/o el nombre del local de este establecimiento. "
    "El rubro se actualiza en el domicilio de origen de esta ficha; las vistas en vivo "
    "que lo leen (esta ficha y actuaciones con ese domicilio) verán el valor nuevo. "
    "El nombre del local se guarda en esta ficha; no se reescriben actuaciones.nombre_local "
    "ni relevamientos.nombre_fantasia. Otros establecimientos del mismo contribuyente no cambian. "
    "No se modifican estados, actas, coordenadas ni PDF ya emitidos."
)


def _ids_payload(ids: list[int], *, sample: int = 20) -> dict[str, Any]:
    ordered = list(ids)
    return {
        "cantidad": len(ordered),
        "ids": ordered[:sample],
    }


def preview_correccion_payload(
    scope: CorreccionScope,
    *,
    propuesto_contrib: dict[str, Any] | None,
    propuesto_dom: dict[str, Any] | None,
    propuesto_local: dict[str, Any] | None = None,
    cambia_contrib: bool,
    cambia_dom: bool,
    cambia_local: bool = False,
    incluir_contrib: bool,
    incluir_dom: bool,
    incluir_local: bool = False,
) -> dict[str, Any]:
    """
    Arma el resumen de alcance para confirmar antes de guardar.

    No afirma actualización de PDF/snapshots. Incluye conflicto si el alcance es inseguro.
    """
    out: dict[str, Any] = {
        "establecimiento_operativo_id": int(scope.eo.id),
        "puede_aplicar": scope.conflicto is None
        and (cambia_contrib or cambia_dom or cambia_local),
        "sin_cambios": not cambia_contrib and not cambia_dom and not cambia_local,
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
    }
    if scope.conflicto:
        out["conflicto"] = {
            "codigo": scope.conflicto_codigo,
            "detail": scope.conflicto,
            "domicilio_ids_ambiguos": scope.lookalike_ids,
        }
        out["puede_aplicar"] = False
        if incluir_dom:
            out["advertencias"].append(scope.conflicto)

    if incluir_contrib:
        out["contribuyente"] = {
            "actual": contribuyente_actual_dict(scope.contribuyente),
            "propuesto": propuesto_contrib,
            "cambia": cambia_contrib,
            "establecimientos_afectados": _ids_payload(scope.establecimiento_ids_contribuyente),
            "actuaciones_afectadas": _ids_payload(scope.actuacion_ids_contribuyente),
            "advertencia": ADVERTENCIA_CONTRIBUYENTE,
        }
        out["advertencias"].append(ADVERTENCIA_CONTRIBUYENTE)

    if incluir_dom:
        actual_dom = domicilio_actual_dict(scope.domicilio)
        out["domicilio"] = {
            "actual": actual_dom,
            "actual_texto": domicilio_texto_visible(scope.domicilio),
            "propuesto": propuesto_dom,
            "cambia": cambia_dom,
            "establecimiento_seleccionado_id": int(scope.eo.id),
            "domicilio_ids_ficha": scope.domicilio_ids_ficha,
            "identidad_logica_completa": scope.identity_completa,
            "actuaciones": _ids_payload(scope.actuacion_ids_domicilio),
            "notificaciones": _ids_payload(scope.notificacion_ids),
            "comprobaciones": _ids_payload(scope.comprobacion_ids),
            "oficios": _ids_payload(scope.oficio_ids),
            "iniciadores": _ids_payload(scope.iniciador_ids),
            "ruta_items": _ids_payload(scope.ruta_item_ids),
            "ruta_estados": scope.ruta_estados[:20],
            "advertencia": ADVERTENCIA_DOMICILIO,
        }
        out["advertencias"].append(ADVERTENCIA_DOMICILIO)

    if incluir_local:
        actual_local = local_actual_dict(scope.eo)
        out["local"] = {
            "actual": actual_local,
            "propuesto": propuesto_local,
            "cambia": cambia_local,
            "establecimiento_seleccionado_id": int(scope.eo.id),
            "domicilio_id": int(scope.domicilio.id),
            "actuaciones_que_leen_rubro": _ids_payload(scope.actuacion_ids_domicilio),
            "otros_establecimientos_contribuyente": _ids_payload(
                [i for i in scope.establecimiento_ids_contribuyente if i != int(scope.eo.id)]
            ),
            "reescribe_actuaciones_nombre_local": False,
            "advertencia": ADVERTENCIA_LOCAL,
        }
        out["advertencias"].append(ADVERTENCIA_LOCAL)

    if not cambia_contrib and not cambia_dom and not cambia_local:
        out["advertencias"].append(ADVERTENCIA_SIN_CAMBIOS)
        out["puede_aplicar"] = False if scope.conflicto else True

    return out


def apply_result_payload(
    preview: dict[str, Any],
    *,
    applied: bool,
    audit_id: int | None,
) -> dict[str, Any]:
    """Resultado de aplicación (mismos recuentos que el preview)."""
    return {
        **preview,
        "applied": applied,
        "audit_id": audit_id,
    }
