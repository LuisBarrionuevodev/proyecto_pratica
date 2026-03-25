from __future__ import annotations

from typing import Any, Dict, List

from app.models import RutaItem

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    tipo_actuacion_esperado_para_iniciador,
)

# Campos de `actuacion_to_grid_row` necesarios para edición inline de cierre (sin previas en UI).
_COMPLETAR_GRID_EXTRA_KEYS: tuple[str, ...] = (
    "numero_tipo",
    "doc_nro",
    "contrib_apellido",
    "contrib_nombre",
    "acta_inspeccion_num",
    "acta_notificacion_num",
    "notificacion_motivo_1",
    "notificacion_motivo_2",
    "notificacion_motivo_3",
    "acta_comprobacion_num",
    "comprobacion_motivo",
    "acta_clausura_num",
    "acta_decomiso_num",
    "decomiso_kilos_total",
)


def _tipo_actuacion_esperado_safe(tipo_iniciador: str | None) -> str | None:
    if not tipo_iniciador:
        return None
    try:
        return tipo_actuacion_esperado_para_iniciador(tipo_iniciador)
    except KeyError:
        return None


def ruta_item_completar_trabajo_to_row(item: RutaItem) -> Dict[str, Any]:
    """
    DTO para la grilla Completar trabajo: contexto de ruta/iniciador + columnas de actuación editables.

    Incluye actas del día y motivos (para edición inline / MRT). No expone actas **previas** como columnas
    dedicadas; el origen queda en `IniciadorRuta`.

    Parámetros:
        item: RutaItem con `actuacion` e `iniciador_ruta` cargados (eager).

    Retorno:
        Dict serializable para JSON.

    Errores:
        ValueError: si falta actuación vinculada.
    """
    act = item.actuacion
    if act is None:
        raise ValueError(f"RutaItem {item.id} sin actuación cargada")

    base = actuacion_to_grid_row(act)
    ini = item.iniciador_ruta

    rubro = base.get("rubro_nombre")
    if not rubro and ini and ini.relevamiento and ini.relevamiento.rubro:
        rubro = ini.relevamiento.rubro.nombre

    calle_m = base.get("calle_mostrar") or base.get("calle")
    num_m = base.get("numero_mostrar") or base.get("numero")
    parts = [p for p in (calle_m, num_m) if p]
    domicilio_texto = " ".join(parts).strip() or None

    insp1, insp2, insp3 = base.get("inspector1"), base.get("inspector2"), base.get("inspector3")
    inspectores_texto = ", ".join(x for x in (insp1, insp2, insp3) if x) or None

    grupo = item.ruta_grupo
    grupo_nombre = grupo.nombre if grupo else None

    tipo_ini = ini.tipo_iniciador if ini else None
    out: Dict[str, Any] = {
        "id": item.id,
        "actuacion_id": act.id,
        "ruta_item_id": item.id,
        "ruta_trabajo_id": item.ruta_trabajo_id,
        "ruta_grupo_id": item.ruta_grupo_id,
        "iniciador_ruta_id": item.iniciador_ruta_id,
        "grupo_nombre": grupo_nombre,
        "fecha_actuacion": base.get("fecha_actuacion"),
        "tipo_iniciador": tipo_ini,
        "iniciador_estado": ini.estado_iniciador if ini else None,
        "orden_trabajo_numero": base.get("orden_trabajo_numero"),
        "tipo_actuacion": base.get("tipo_actuacion"),
        "contraproducencia": base.get("contraproducencia"),
        "calle": base.get("calle"),
        "numero": base.get("numero"),
        "domicilio_texto": domicilio_texto,
        "rubro_nombre": rubro,
        "inspectores_texto": inspectores_texto,
        "estado_operativo": item.estado_ruta_item,
        "observaciones_ejecucion": item.observaciones_ejecucion,
        "tipo_actuacion_esperado": _tipo_actuacion_esperado_safe(tipo_ini),
    }
    for k in _COMPLETAR_GRID_EXTRA_KEYS:
        out[k] = base.get(k)
    return out


def ruta_item_completar_trabajo_detalle(
    item: RutaItem,
    *,
    inspectores_grupo: List[Dict[str, Any]],
    tipo_actuacion_esperado: str | None,
) -> Dict[str, Any]:
    """
    Respuesta GET detalle Completar trabajo: fila + inspectores de grupo + políticas UI.

    Parámetros:
        item: RutaItem con relaciones cargadas (como en listado).
        inspectores_grupo: inspectores asignados al grupo de la ruta (solo lectura en UI).
        tipo_actuacion_esperado: tipo de catálogo coherente con `tipo_iniciador` (si aplica).

    Retorno:
        Dict con `row`, `inspectores_grupo`, `ui_policy`, `tipo_actuacion_esperado`.
    """
    row = ruta_item_completar_trabajo_to_row(item)

    return {
        "row": row,
        "inspectores_grupo": inspectores_grupo,
        "tipo_actuacion_esperado": tipo_actuacion_esperado,
        "ui_policy": {
            "recurso_logico": "actuacion",
            "ancla_operativa": "ruta_item",
            "orden_trabajo_y_fecha_readonly": True,
            "inspectores_readonly": True,
            "previas_visible": False,
            "post_cierre": "POST /actuaciones/completar-trabajo/cerrar/<ruta_item_id>",
        },
    }
