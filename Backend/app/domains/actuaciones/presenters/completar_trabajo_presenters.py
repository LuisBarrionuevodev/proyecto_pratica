from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import joinedload

from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_nombre_operativo_para_iniciador
from app.models import Actuaciones, Domicilio, RutaGrupo, RutaItem

from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.services.completar_trabajo_tipo_iniciador import (
    tipo_actuacion_esperado_para_iniciador,
)

# Campos de `actuacion_to_grid_row` necesarios para edición inline de cierre (sin previas en UI).
_COMPLETAR_GRID_EXTRA_KEYS: tuple[str, ...] = (
    "establecimiento_operativo_id",
    "establecimiento_actuaciones_en_ficha",
    "nombre_local",
    "numero_tipo",
    "doc_nro",
    "contrib_apellido",
    "contrib_nombre",
    "razon_social",
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
    "resultado_cumplimiento_oficio",
)


def _tipo_actuacion_esperado_safe(tipo_iniciador: str | None) -> str | None:
    if not tipo_iniciador:
        return None
    try:
        return tipo_actuacion_esperado_para_iniciador(tipo_iniciador)
    except KeyError:
        return None


def _snapshot_contrib_prefill(contrib: Any) -> dict[str, Any]:
    """Snapshot mínimo de contribuyente para prefill en Completar trabajo."""
    if contrib is None:
        return {}
    doc = getattr(contrib, "documento", None) or getattr(contrib, "doc_nro", None)
    if not doc or not str(doc).strip():
        return {}
    return {
        "doc_nro": str(doc).strip(),
        "contrib_apellido": getattr(contrib, "apellido", None),
        "contrib_nombre": getattr(contrib, "nombre", None),
        "razon_social": getattr(contrib, "razon_social", None),
    }


def _enrich_contrib_prefill_oficio(row: Dict[str, Any], item: RutaItem) -> Dict[str, Any]:
    """
    Completa titular/documento en filas de oficio cuando la actuación publicada aún no los trae.

    Prioridad: actuación origen del iniciador → domicilio del iniciador → domicilio de la actuación.
    """
    if row.get("doc_nro"):
        return row
    ini = item.iniciador_ruta
    if ini is None:
        return row
    tipo = (ini.tipo_iniciador or "").strip()
    if tipo not in (
        "REINSPECCION_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        return row

    candidates: list[Any] = []
    if ini.actuacion_id:
        origin = (
            Actuaciones.query.options(
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente)
            )
            .filter(Actuaciones.id == int(ini.actuacion_id))
            .first()
        )
        if origin and origin.domicilio and origin.domicilio.contribuyente:
            candidates.append(origin.domicilio.contribuyente)
    if ini.domicilio and ini.domicilio.contribuyente:
        candidates.append(ini.domicilio.contribuyente)
    act = item.actuacion
    if act and act.domicilio and act.domicilio.contribuyente:
        candidates.append(act.domicilio.contribuyente)

    for contrib in candidates:
        snap = _snapshot_contrib_prefill(contrib)
        if snap:
            merged = dict(row)
            merged.update({k: v for k, v in snap.items() if v is not None})
            return merged
    return row


def _nombres_inspectores_grupo(grupo: Optional[RutaGrupo]) -> list[str]:
    """Nombres ordenados por id de relación; la actuación al publicar no copia inspectores al act."""
    if grupo is None:
        return []
    rels = getattr(grupo, "grupo_inspectores", None) or []
    out: list[str] = []
    for rel in sorted(rels, key=lambda x: x.id):
        ins = getattr(rel, "inspector", None)
        n = getattr(ins, "nombre", None) if ins else None
        if n and str(n).strip():
            out.append(str(n).strip())
    return out


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

    ini = item.iniciador_ruta
    base = actuacion_to_grid_row(act, iniciador_desde_ruta=ini)

    rubro = rubro_nombre_operativo_para_iniciador(ini, act.domicilio, act=act)
    if rubro is None and (not ini or ini.tipo_iniciador != "DENUNCIA"):
        rubro = base.get("rubro_nombre")

    calle_m = (base.get("calle_mostrar") or base.get("calle") or "").strip()
    num_m = (base.get("numero_mostrar") or base.get("numero") or "").strip()
    nt = (base.get("numero_tipo") or "").strip().upper()
    esq_norm = (base.get("esquina_normalizada") or "").strip()
    if nt == "ESQUINA":
        esq_effective = esq_norm or num_m
        if calle_m and esq_effective:
            domicilio_texto = f"{calle_m} Y {esq_effective}"
        else:
            domicilio_texto = " ".join(p for p in (calle_m, num_m) if p).strip() or None
    else:
        parts = [p for p in (calle_m, num_m) if p]
        domicilio_texto = " ".join(parts).strip() or None

    grupo = item.ruta_grupo
    insp1, insp2, insp3 = base.get("inspector1"), base.get("inspector2"), base.get("inspector3")
    inspectores_texto = ", ".join(x for x in (insp1, insp2, insp3) if x) or None
    if not inspectores_texto and grupo is not None:
        nombres_g = _nombres_inspectores_grupo(grupo)
        if nombres_g:
            inspectores_texto = ", ".join(nombres_g)
            insp1 = nombres_g[0] if len(nombres_g) > 0 else insp1
            insp2 = nombres_g[1] if len(nombres_g) > 1 else insp2
            insp3 = nombres_g[2] if len(nombres_g) > 2 else insp3

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
        "calle": base.get("calle_cargada") or base.get("calle"),
        "calle_raw": base.get("calle_raw"),
        "calle_cargada": base.get("calle_cargada"),
        "calle_normalizada": base.get("calle_normalizada"),
        "calle_estado": base.get("calle_estado"),
        "calle_mostrar": base.get("calle_mostrar"),
        "numero": base.get("numero"),
        "numero_tipo": base.get("numero_tipo"),
        "numero_esquina": base.get("numero_esquina"),
        "esquina_raw": base.get("esquina_raw"),
        "esquina_normalizada": base.get("esquina_normalizada"),
        "esquina_cargada": base.get("esquina_cargada"),
        "esquina_key": base.get("esquina_key"),
        "esquina_status": base.get("esquina_status"),
        "domicilio_texto": domicilio_texto,
        "domicilio_id": base.get("domicilio_id"),
        "rubro_nombre": rubro,
        "inspectores_texto": inspectores_texto,
        "inspector1": insp1,
        "inspector2": insp2,
        "inspector3": insp3,
        "estado_operativo": item.estado_ruta_item,
        "observaciones_ejecucion": item.observaciones_ejecucion,
        "tipo_actuacion_esperado": _tipo_actuacion_esperado_safe(tipo_ini),
    }
    for k in _COMPLETAR_GRID_EXTRA_KEYS:
        out[k] = base.get(k)
    return _enrich_contrib_prefill_oficio(out, item)


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


def dia_resumen_completar_trabajo_pendientes(
    *,
    fecha_dia: date,
    total: int,
    items_con_actuacion: int,
    hoy: date,
) -> Dict[str, Any]:
    """
    Presenta un día del resumen operativo Completar trabajo (carrusel + calendario).

    Parámetros:
        fecha_dia: día operativo de la ruta (`RutaTrabajo.fecha`).
        total: ítems EN_PROCESO con actuación (pendientes de cierre), mismo criterio que el listado por fecha.
        items_con_actuacion: ítems con `actuacion_id` en rutas PUBLICADAS ese día (ámbito del módulo).
        hoy: fecha de referencia para `atrasado` (día pasado con pendientes de cierre).

    Retorno:
        Dict con `fecha`, `total`, `atrasado`, `items_con_actuacion`, `hubo_actividad`,
        `sin_pendientes_cierre`, `categoria_calendario` (`CON_PENDIENTES` | `COMPLETO`).

    Errores:
        Ninguno. Si `items_con_actuacion` fuera 0, el llamador no debería incluir la fila.

    Nota:
        Día **sin actividad** en calendario: fecha sin fila en el agregado (no hay ítems con actuación
        en ruta publicada ese día en el rango consultado).
    """
    total_i = int(total)
    items_i = int(items_con_actuacion)
    hubo = items_i > 0
    sin_pend = hubo and total_i == 0
    categoria = "CON_PENDIENTES" if total_i > 0 else "COMPLETO"
    atrasado = bool(fecha_dia < hoy and total_i > 0)
    return {
        "fecha": fecha_dia.isoformat(),
        "total": total_i,
        "atrasado": atrasado,
        "items_con_actuacion": items_i,
        "hubo_actividad": hubo,
        "sin_pendientes_cierre": sin_pend,
        "categoria_calendario": categoria,
    }
