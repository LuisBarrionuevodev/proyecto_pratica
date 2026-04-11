"""
Presentación para bandejas de Actas de comprobación (reinspección oficio / recorrido).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    expediente_envio_por_comprobacion,
    oficio_por_comprobacion,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.models import Actuaciones, Expediente, IniciadorRuta


def _expediente_respuesta_oficio(comprobacion_id: int) -> Optional[Expediente]:
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id)
        .filter(Expediente.oficio_id.isnot(None))
        .filter(Expediente.tipo_expediente == "RESPUESTA_OFICIO")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.desc())
        .first()
    )


def estado_recorrido_label(act: Actuaciones) -> str:
    """
    Etiqueta consultiva del estado del circuito documental para la fila de actuación.
    """
    if not act.comprobacion_id:
        return "—"
    ofi = oficio_por_comprobacion(act.comprobacion_id)
    if not ofi:
        return "Esperando oficio"

    ini = (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == act.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if not ini:
        return "Oficio cargado — sin reinspección programada"
    if ini.estado_iniciador == "CUMPLIDO":
        return "Reinspección cumplida"
    if ini.estado_iniciador in inactive_estados():
        return f"Cerrado ({ini.estado_iniciador})"
    return "Pendiente reinspección por oficio"


def iniciador_reinspeccion_to_row(
    ini: IniciadorRuta,
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    """Fila para bandeja Pendientes de reinspección (oficio ya cargado)."""
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    return {
        "iniciador_id": ini.id,
        "estado_iniciador": ini.estado_iniciador,
        "tipo_iniciador": ini.tipo_iniciador,
        "fecha_origen_iniciador": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
        "id": base.get("id"),
        "fecha_actuacion": base.get("fecha_actuacion"),
        "orden_trabajo_numero": base.get("orden_trabajo_numero"),
        "acta_comprobacion_num": base.get("acta_comprobacion_num"),
        "comprobacion_motivo": base.get("comprobacion_motivo"),
        "rubro_nombre": base.get("rubro_nombre"),
        "calle": base.get("calle"),
        "numero": base.get("numero"),
        "contrib_apellido": base.get("contrib_apellido"),
        "contrib_nombre": base.get("contrib_nombre"),
        "oficio_numero": base.get("oficio_numero"),
        "oficio_anio": base.get("oficio_anio"),
        "documento_pendiente": "Reinspección por oficio",
    }


def comprobacion_recorrido_resumen_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    base["estado_recorrido"] = estado_recorrido_label(act)
    return base


def comprobacion_recorrido_detalle(act: Actuaciones) -> Dict[str, Any]:
    """
    Detalle estructurado consultivo (sin PDF): origen, comprobación, expedientes, oficio, reinspección, resultado.
    """
    if not act.comprobacion_id:
        raise ValueError("La actuación no tiene comprobación")

    grid = actuacion_to_grid_row(act)
    exp_env = expediente_envio_por_comprobacion(act.comprobacion_id)
    ofi = oficio_por_comprobacion(act.comprobacion_id)
    exp_resp = _expediente_respuesta_oficio(act.comprobacion_id)

    ini = (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == act.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )

    resultado = getattr(act, "resultado_cumplimiento_oficio", None)
    res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado

    return {
        "actuacion_id": act.id,
        "origen": {
            "descripcion": "Actuación con acta de comprobación",
            "fecha_actuacion": grid.get("fecha_actuacion"),
            "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
        },
        "acta_comprobacion": {
            "numero": grid.get("acta_comprobacion_num"),
            "motivo": grid.get("comprobacion_motivo"),
        },
        "expediente_comprobacion_envio": (
            {
                "id": exp_env.id,
                "numero": exp_env.numero_expediente,
                "anio": exp_env.anio,
                "fecha": exp_env.fecha_expediente.isoformat() if exp_env.fecha_expediente else None,
                "tipo": exp_env.tipo_expediente,
            }
            if exp_env
            else None
        ),
        "oficio": (
            {
                "id": ofi.id,
                "numero_oficio": ofi.numero_oficio,
                "anio": ofi.anio,
                "fecha_oficio": ofi.fecha_oficio.isoformat() if ofi.fecha_oficio else None,
            }
            if ofi
            else None
        ),
        "expediente_respuesta_oficio": (
            {
                "id": exp_resp.id,
                "numero": exp_resp.numero_expediente,
                "anio": exp_resp.anio,
                "fecha": exp_resp.fecha_expediente.isoformat() if exp_resp.fecha_expediente else None,
                "tipo": exp_resp.tipo_expediente,
            }
            if exp_resp
            else None
        ),
        "reinspeccion_por_oficio": (
            {
                "iniciador_id": ini.id,
                "estado_iniciador": ini.estado_iniciador,
                "fecha_origen": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
            }
            if ini
            else None
        ),
        "resultado_final": {
            "resultado_cumplimiento_oficio": res_val,
            "estado_recorrido": estado_recorrido_label(act),
        },
    }
