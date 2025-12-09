from __future__ import annotations

from typing import Any, Dict, Optional

from app.schemas.grid.actuacion_row import ActuacionGridRowIn


def map_actuacion_row(row: ActuacionGridRowIn) -> Dict[str, Any]:
    """
    recibe y mapea todo e
    """

    inspectores = [x for x in (row.inspector1, row.inspector2, row.inspector3) if x]

    motivos_notificacion = [
        x for x in (row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3)
        if x
    ]

    domicilio: Optional[Dict[str, Any]] = None
    if row.calle and row.numero:
        domicilio = {
            "calle": row.calle,
            "numero": row.numero,
        }

    contribuyente: Optional[Dict[str, Any]] = None
    if row.doc_nro or row.contrib_apellido or row.contrib_nombre:
        contribuyente = {
            "doc_nro": row.doc_nro,
            "apellido": row.contrib_apellido,
            "nombre": row.contrib_nombre,
        }

    #  solo armamos notificación si hay número de acta
    notificacion: Optional[Dict[str, Any]] = None
    if row.acta_notificacion_num:
        notificacion = {
            "acta_num": row.acta_notificacion_num,
            "motivos": motivos_notificacion,
        }

    # solo armamos comprobación si hay número de acta
    comprobacion: Optional[Dict[str, Any]] = None
    if row.acta_comprobacion_num:
        comprobacion = {
            "acta_num": row.acta_comprobacion_num,
            "motivo": row.comprobacion_motivo,
        }

    clausura: Optional[Dict[str, Any]] = None
    if row.acta_clausura_num:
        clausura = {
            "acta_num": row.acta_clausura_num,
        }

    decomiso: Optional[Dict[str, Any]] = None
    if row.acta_decomiso_num:
        decomiso = {
            "acta_num": row.acta_decomiso_num,
            "kilos_total": row.decomiso_kilos_total,
        }

    expediente: Optional[Dict[str, Any]] = None
    if row.expediente_numero and row.expediente_anio is not None:
        expediente = {
            "numero": row.expediente_numero,
            "anio": row.expediente_anio,
        }

    oficio: Optional[Dict[str, Any]] = None
    hay_oficio = row.oficio_numero or (row.oficio_anio is not None) or row.oficio_causa
    if hay_oficio:
        oficio = {
            "numero": row.oficio_numero,
            "anio": row.oficio_anio,
            "causa": row.oficio_causa,  # opcional
            "comprobacion_previa_num": row.comprobacion_previa_num,
        }

    previas: Optional[Dict[str, Any]] = None
    if row.notificacion_previa_num or row.comprobacion_previa_num:
        previas = {
            "notificacion_previa_num": row.notificacion_previa_num,
            "comprobacion_previa_num": row.comprobacion_previa_num,
        }

    payload: Dict[str, Any] = {
        "orden_trabajo_numero": row.orden_trabajo_numero,
        "fecha_actuacion": row.fecha_actuacion,
        "tipo_actuacion": row.tipo_actuacion,
        "contraproducencia": row.contraproducencia,

        "rubro_nombre": row.rubro_nombre,
        "inspectores": inspectores,

        "domicilio": domicilio,
        "contribuyente": contribuyente,

        "acta_inspeccion_num": row.acta_inspeccion_num,

        "notificacion": notificacion,
        "comprobacion": comprobacion,

        "clausura": clausura,
        "decomiso": decomiso,

        "expediente": expediente,
        "oficio": oficio,

        "previas": previas,
    }

    return payload
