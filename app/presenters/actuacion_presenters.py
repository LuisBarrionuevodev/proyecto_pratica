from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import Actuaciones


def actuacion_to_grid_row(act: Actuaciones) -> Dict[str, Any]:
    """
    Convierte una Actuación (con relaciones) al formato plano
    que espera tu Material React Table.
    """

    # OT
    ot_num = act.orden_trabajo.numero_acta if act.orden_trabajo else None

    # Fecha en string tipo DD/MM/YYYY para que sea consistente con tu grid
    fecha_str = act.fecha.strftime("%d/%m/%Y") if act.fecha else None

    # Rubro / domicilio / contribuyente
    rubro_nombre: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None

    if act.domicilio:
        calle = act.domicilio.calle
        numero = act.domicilio.numero

        if act.domicilio.rubro:
            rubro_nombre = act.domicilio.rubro.nombre

        if act.domicilio.contribuyente:
            doc_nro = act.domicilio.contribuyente.documento
            contrib_apellido = act.domicilio.contribuyente.apellido
            contrib_nombre = act.domicilio.contribuyente.nombre

    # Inspectores (max 3)
    nombres = []
    if act.inspector:
        nombres = [i.nombre for i in act.inspector]

    inspector1 = nombres[0] if len(nombres) > 0 else None
    inspector2 = nombres[1] if len(nombres) > 1 else None
    inspector3 = nombres[2] if len(nombres) > 2 else None

    # Actas principales
    acta_inspeccion_num = act.inspeccion.numero_acta if act.inspeccion else None
    acta_clausura_num = act.clausura.numero_acta if act.clausura else None
    acta_decomiso_num = act.decomiso.numero_acta if act.decomiso else None
    decomiso_kilos_total = act.decomiso.cantidad if act.decomiso else None

    # Notificación / comprobación simples
    acta_notificacion_num = act.notificacion.numero_acta if act.notificacion else None
    acta_comprobacion_num = act.comprobacion.numero_acta if act.comprobacion else None
    comprobacion_motivo = act.comprobacion.motivo if act.comprobacion else None

    # Motivos de notificación (si querés mostrarlos)
    motivos = []
    if act.notificacion and getattr(act.notificacion, "motivos", None):
        motivos = [m.nombre for m in act.notificacion.motivos]

    notificacion_motivo_1 = motivos[0] if len(motivos) > 0 else None
    notificacion_motivo_2 = motivos[1] if len(motivos) > 1 else None
    notificacion_motivo_3 = motivos[2] if len(motivos) > 2 else None

    # Expediente / Oficio
    expediente_numero = None
    expediente_anio = None
    oficio_numero = None
    oficio_anio = None
    oficio_causa = None

    # Si tu relación de expediente está en otro lado, esto lo ajustamos después
    # por ahora lo dejamos plano en None si no lo tenés directo.

    return {
        "id": act.id,
        "orden_trabajo_numero": ot_num,
        "fecha_actuacion": fecha_str,

        "rubro_nombre": rubro_nombre,

        "inspector1": inspector1,
        "inspector2": inspector2,
        "inspector3": inspector3,

        "calle": calle,
        "numero": numero,

        "tipo_actuacion": str(act.tipo) if act.tipo else None,
        "contraproducencia": str(act.contraproducencia) if act.contraproducencia else None,

        "doc_nro": doc_nro,
        "contrib_apellido": contrib_apellido,
        "contrib_nombre": contrib_nombre,

        "acta_inspeccion_num": acta_inspeccion_num,

        "acta_notificacion_num": acta_notificacion_num,
        "notificacion_motivo_1": notificacion_motivo_1,
        "notificacion_motivo_2": notificacion_motivo_2,
        "notificacion_motivo_3": notificacion_motivo_3,

        "acta_comprobacion_num": acta_comprobacion_num,
        "comprobacion_motivo": comprobacion_motivo,

        "acta_clausura_num": acta_clausura_num,

        "acta_decomiso_num": acta_decomiso_num,
        "decomiso_kilos_total": decomiso_kilos_total,

        "expediente_numero": expediente_numero,
        "expediente_anio": expediente_anio,

        "oficio_numero": oficio_numero,
        "oficio_anio": oficio_anio,
        "oficio_causa": oficio_causa,

        "notificacion_previa_num": None,
        "comprobacion_previa_num": None,
    }
