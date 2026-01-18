from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Actuaciones


def actuacion_to_list_item(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una Actuaciones (modelo DB) a un DTO simplificado para listados.
    
    Incluye solo los campos más relevantes para la vista de tabla.
    
    Args:
        act: Instancia de Actuaciones con relaciones cargadas.
    
    Returns:
        {
            "id": 1,
            "fecha_actuacion": "2025-01-14",
            "tipo_actuacion": "INSPECCION",
            "contraproducencia": "NO_HUBO",
            "orden_trabajo_numero": "123",
            "inspector1": "PEREZ",
            "calle": "AV CORDOBA",
            "numero": "1234",
            "rubro_nombre": "CARNICERIA",
            "acta_inspeccion_num": "456",
            "acta_notificacion_num": "789",
            "acta_comprobacion_num": "012"
        }
    """
    # OT
    ot_num: Optional[str] = None
    if getattr(act, "orden_trabajo", None):
        ot_num = (
            getattr(act.orden_trabajo, "numero_acta", None)
            or getattr(act.orden_trabajo, "numero", None)
        )
    
    # Fecha ISO
    fecha_iso: Optional[str] = act.fecha.isoformat() if act.fecha else None
    
    # Domicilio/Rubro
    calle: Optional[str] = None
    numero: Optional[str] = None
    rubro_nombre: Optional[str] = None
    
    dom = getattr(act, "domicilio", None)
    if dom:
        calle = getattr(dom, "calle", None)
        numero = getattr(dom, "numero", None)
        
        rub = getattr(dom, "rubro", None)
        if rub:
            rubro_nombre = getattr(rub, "nombre", None)
    
    # Inspectores
    inspector1 = None
    insp_list = getattr(act, "inspector", None) or []
    if insp_list:
        nombres = [getattr(i, "nombre", None) for i in insp_list if getattr(i, "nombre", None)]
        if nombres:
            inspector1 = nombres[0]
    
    # Actas principales
    inspeccion = getattr(act, "inspeccion", None)
    noti = getattr(act, "notificacion", None)
    comp = getattr(act, "comprobacion", None)
    
    acta_inspeccion_num = getattr(inspeccion, "numero_acta", None) if inspeccion else None
    acta_notificacion_num = getattr(noti, "numero_acta", None) if noti else None
    acta_comprobacion_num = getattr(comp, "numero_acta", None) if comp else None
    
    # Enum to string
    def enum_to_str(value):
        if value is None:
            return None
        name = getattr(value, "name", None)
        if name:
            return str(name)
        s = str(value).strip()
        if "." in s:
            s = s.split(".")[-1].strip()
        return s or None
    
    return {
        "id": act.id,
        "fecha_actuacion": fecha_iso,
        "tipo_actuacion": enum_to_str(getattr(act, "tipo", None)),
        "contraproducencia": enum_to_str(getattr(act, "contraproducencia", None)),
        "orden_trabajo_numero": ot_num,
        "inspector1": inspector1,
        "calle": calle,
        "numero": numero,
        "rubro_nombre": rubro_nombre,
        "acta_inspeccion_num": acta_inspeccion_num,
        "acta_notificacion_num": acta_notificacion_num,
        "acta_comprobacion_num": acta_comprobacion_num,
    }
