"""
Serialización JSON para API de fichas ``establecimiento_operativo``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Actuaciones, EstablecimientoOperativo


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
) -> Dict[str, Any]:
    """
    Detalle de ficha + agregados de actuaciones para cabecera UI.

    Parámetros:
        eo: instancia con relaciones cargadas.
        actuaciones_count: total de actuaciones con esta ficha.
        ultima_actuacion_fecha: ``date`` o None.

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
    return base


def actuacion_historial_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Una fila de historial (actuación vinculada a la ficha).

    Parámetros:
        act: ``Actuaciones`` con ``orden_trabajo`` e ``inspeccion`` opcionalmente cargados.

    Retorno:
        dict con campos mínimos para tabla de historial.
    """
    ot_num: Optional[str] = None
    if getattr(act, "orden_trabajo", None):
        ot_num = getattr(act.orden_trabajo, "numero_acta", None) or getattr(
            act.orden_trabajo, "numero", None
        )
    inspeccion = getattr(act, "inspeccion", None)
    acta_inspeccion_num = getattr(inspeccion, "numero_acta", None) if inspeccion else None

    fecha_iso = act.fecha.isoformat() if act.fecha else None

    return {
        "id": act.id,
        "fecha": fecha_iso,
        "tipo_actuacion": _enum_or_str(getattr(act, "tipo", None)),
        "contraproducencia": _enum_or_str(getattr(act, "contraproducencia", None)),
        "nombre_local": (str(act.nombre_local).strip() or None) if act.nombre_local else None,
        "orden_trabajo_numero": ot_num,
        "acta_inspeccion_num": acta_inspeccion_num,
    }
