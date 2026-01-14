from __future__ import annotations

"""
Column mapping para el dominio "actuaciones".

Glide usa headers "human-friendly" (con espacios). Internamente usamos snake_case
para validar con Pydantic y mapear a payload canon.
"""

# Glide header -> key interna (snake_case)
COLUMN_MAP_ACTUACIONES: dict[str, str] = {
    "ID": "id",
    "Fecha actuación": "fecha_actuacion",
    "Tipo actuación": "tipo_actuacion",
    "Contraproducencia": "contraproducencia",
    "Orden de trabajo": "orden_trabajo_numero",
    "Inspector 1": "inspector1",
    "Inspector 2": "inspector2",
    "Inspector 3": "inspector3",
    "Calle": "calle",
    "Número": "numero",
    "Rubro": "rubro_nombre",
    "Apellido": "contrib_apellido",
    "Nombre": "contrib_nombre",
    "DNI": "doc_nro",
    "Acta inspección": "acta_inspeccion_num",
    "Acta notificación": "acta_notificacion_num",
    "Motivo notif 1": "notificacion_motivo_1",
    "Motivo notif 2": "notificacion_motivo_2",
    "Motivo notif 3": "notificacion_motivo_3",
    "Acta comprobación": "acta_comprobacion_num",
    "Motivo comprobación": "comprobacion_motivo",
    "Acta clausura": "acta_clausura_num",
    "Acta decomiso": "acta_decomiso_num",
    "Kilos decomiso": "decomiso_kilos_total",
    "Acta notificación previa": "notificacion_previa_num",
    "Acta comprobación previa": "comprobacion_previa_num",
    "Expediente año": "expediente_anio",
    "Expediente número": "expediente_numero",
    "Oficio año": "oficio_anio",
    "Oficio número": "oficio_numero",
    "Oficio causa": "oficio_causa",
}

