from __future__ import annotations

from typing import Optional
from datetime import date

from pydantic import BaseModel


class ActuacionPatchIn(BaseModel):
    """
    Schema para actualizaciones parciales (PATCH) de actuaciones.
    Todos los campos son opcionales - solo se actualizan los que se envíen.
    """
    # Campos básicos
    orden_trabajo_numero: Optional[str] = None
    fecha_actuacion: Optional[date | str] = None
    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None
    
    # Rubro y domicilio
    rubro_nombre: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    
    # Inspectores
    inspector1: Optional[str] = None
    inspector2: Optional[str] = None
    inspector3: Optional[str] = None
    
    # Contribuyente
    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    
    # Actas
    acta_inspeccion_num: Optional[str] = None
    acta_notificacion_num: Optional[str] = None
    notificacion_motivo_1: Optional[str] = None
    notificacion_motivo_2: Optional[str] = None
    notificacion_motivo_3: Optional[str] = None
    acta_comprobacion_num: Optional[str] = None
    comprobacion_motivo: Optional[str] = None
    acta_clausura_num: Optional[str] = None
    acta_decomiso_num: Optional[str] = None
    decomiso_kilos_total: Optional[float] = None
    
    # Expediente y oficio
    expediente_numero: Optional[str] = None
    expediente_anio: Optional[int] = None
    oficio_numero: Optional[str] = None
    oficio_anio: Optional[int] = None
    oficio_causa: Optional[str] = None
    
    # Previas
    notificacion_previa_num: Optional[str] = None
    comprobacion_previa_num: Optional[str] = None

    class Config:
        # Permite pasar campos extra sin error
        extra = "ignore"
