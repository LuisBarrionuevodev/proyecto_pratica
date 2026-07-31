"""
Serialización JSON para API de fichas ``establecimiento_operativo``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domains.actuaciones.presenters.actuacion_presenters import (
    ActuacionGridBatchMaps,
    build_actuacion_grid_batch_maps,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.establecimientos.presenters.historial_contribuyente_presenters import (
    build_actas_tramites_payload_for_actuacion,
    contraproducencia_historial_visible,
    inspectores_historial_texto,
)
from app.domains.establecimientos.utils.domicilio_display import (
    domicilio_texto_ficha_detalle,
    domicilio_texto_historial_fila,
    domicilio_texto_visible,
)
from app.models import Actuaciones, Domicilio, EstablecimientoOperativo, RutaItem


def _enum_or_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    s = str(val).strip()
    return s or None


def establecimiento_operativo_list_row(eo: EstablecimientoOperativo) -> Dict[str, Any]:
    """
    Fila de listado: ficha + datos de presentación desde domicilio/contribuyente/rubro/distrito.

    Parámetros:
        eo: instancia con ``domicilio`` cargado (y relaciones de domicilio resueltas).

    Retorno:
        dict serializable para JSON.
    """
    dom = eo.domicilio
    out: Dict[str, Any] = {
        "id": eo.id,
        "domicilio_id": eo.domicilio_id,
        "created_at": eo.created_at.isoformat() if eo.created_at else None,
        "updated_at": eo.updated_at.isoformat() if eo.updated_at else None,
    }
    if not dom:
        out.update(
            {
                "calle": None,
                "numero": None,
                "calle_normalizada": None,
                "domicilio_texto": None,
                "contrib_apellido": None,
                "contrib_nombre": None,
                "razon_social": None,
                "documento": None,
                "rubro_nombre": None,
                "distrito_id": None,
                "distrito_nombre": None,
            }
        )
        return out

    rub = getattr(dom, "rubro", None)
    dist = getattr(dom, "distrito", None)
    contrib = getattr(dom, "contribuyente", None)

    out.update(
        {
            "calle": dom.calle,
            "numero": dom.numero,
            "calle_normalizada": getattr(dom, "calle_normalizada", None),
            "domicilio_texto": domicilio_texto_visible(dom),
            "contrib_apellido": getattr(contrib, "apellido", None) if contrib else None,
            "contrib_nombre": getattr(contrib, "nombre", None) if contrib else None,
            "razon_social": getattr(contrib, "razon_social", None) if contrib else None,
            "documento": getattr(contrib, "documento", None) if contrib else None,
            "rubro_nombre": getattr(rub, "nombre", None) if rub else None,
            "distrito_id": dom.distrito_id,
            "distrito_nombre": getattr(dist, "nombre", None) if dist else None,
        }
    )
    return out


def establecimiento_operativo_detail(
    eo: EstablecimientoOperativo,
    *,
    actuaciones_count: int,
    ultima_actuacion_fecha: Any | None,
    domicilio_ultima_actuacion: Domicilio | None = None,
) -> Dict[str, Any]:
    """
    Detalle de ficha + agregados de actuaciones para cabecera UI.

    Parámetros:
        eo: instancia con relaciones cargadas.
        actuaciones_count: total de actuaciones con esta ficha.
        ultima_actuacion_fecha: ``date`` o None.
        domicilio_ultima_actuacion: domicilio de la actuación más reciente, si existe.

    Retorno:
        dict serializable (incluye bloque ``list_row`` plano y metadatos).
    """
    base = establecimiento_operativo_list_row(eo)
    uaf = None
    if ultima_actuacion_fecha is not None:
        uaf = (
            ultima_actuacion_fecha.isoformat()
            if hasattr(ultima_actuacion_fecha, "isoformat")
            else str(ultima_actuacion_fecha)
        )
    base["actuaciones_count"] = int(actuaciones_count)
    base["ultima_actuacion_fecha"] = uaf
    base["domicilio_texto"] = domicilio_texto_ficha_detalle(
        eo.domicilio if eo else None,
        domicilio_ultima_actuacion,
    )
    return base


def _load_ruta_items_by_actuacion_id(act_ids: List[int]) -> Dict[int, RutaItem]:
    """
    Mapa ``actuacion_id`` → ``RutaItem`` para derivar contraproducencia en NO_REALIZADO.

    Parámetros:
        act_ids: ids de actuaciones de la página.

    Retorno:
        dict indexado por ``actuacion_id``.
    """
    if not act_ids:
        return {}
    rows = (
        RutaItem.query.filter(
            RutaItem.actuacion_id.in_(act_ids),
            RutaItem.deleted_at.is_(None),
        ).all()
    )
    out: Dict[int, RutaItem] = {}
    for ri in rows:
        if ri.actuacion_id is not None:
            out[int(ri.actuacion_id)] = ri
    return out


def actuacion_historial_row(
    act: Actuaciones,
    *,
    iniciador: Any = None,
    batch: ActuacionGridBatchMaps | None = None,
    ruta_item: RutaItem | None = None,
) -> Dict[str, Any]:
    """
    Una fila de historial (actuación vinculada a la ficha).

    Parámetros:
        act: ``Actuaciones`` con relaciones de actas y trámites cargadas.
        iniciador: iniciador de ruta opcional (reinspección notificación).
        batch: mapas batch de expedientes/oficios.

    Retorno:
        dict con campos para tabla de historial (tipo, contraproducencia, actas/trámites).
    """
    fecha_iso = act.fecha.isoformat() if act.fecha else None
    doc = build_actas_tramites_payload_for_actuacion(act, iniciador=iniciador, batch=batch)

    return {
        "id": act.id,
        "fecha": fecha_iso,
        "tipo_actuacion": _enum_or_str(getattr(act, "tipo", None)),
        "contraproducencia": contraproducencia_historial_visible(act, ruta_item),
        "inspectores_texto": inspectores_historial_texto(act),
        "domicilio_texto": domicilio_texto_historial_fila(act, iniciador=iniciador),
        **doc,
    }


def actuacion_historial_rows(acts: List[Actuaciones]) -> List[Dict[str, Any]]:
    """
    Presenta un lote de actuaciones de historial con mapas batch compartidos.

    Parámetros:
        acts: actuaciones de la página actual.

    Retorno:
        Lista de dicts listos para JSON.
    """
    if not acts:
        return []

    act_ids = [int(a.id) for a in acts if a.id is not None]
    ini_map = build_iniciador_ruta_por_actuacion_id(act_ids)
    batch = build_actuacion_grid_batch_maps(acts, ini_map)
    ruta_items_by_act = _load_ruta_items_by_actuacion_id(act_ids)

    return [
        actuacion_historial_row(
            act,
            iniciador=ini_map.get(int(act.id)) if act.id is not None else None,
            batch=batch,
            ruta_item=ruta_items_by_act.get(int(act.id)) if act.id is not None else None,
        )
        for act in acts
    ]
