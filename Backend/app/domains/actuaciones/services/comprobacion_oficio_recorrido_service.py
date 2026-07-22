"""
Campos operativos de recorrido por oficio (OT, conclusión, ejecución de reinspección).

Un oficio puede tener su propio iniciador ``REINSPECCION_OFICIO``, ruta item y actuación de cierre.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import Actuaciones, IniciadorRuta, Oficio, OrdenTrabajo, RutaItem

_CUMPLIMIENTO_LABEL = {
    "CUMPLE": "Cumple",
    "NO_CUMPLE": "No cumple",
}


def iniciador_reinspeccion_por_oficio(oficio_id: int) -> IniciadorRuta | None:
    """
    Iniciador activo ``REINSPECCION_OFICIO`` vinculado al oficio (excluye anulados/soft-deleted).

    Parámetros:
        oficio_id: PK de ``Oficio``.

    Retorno:
        ``IniciadorRuta`` o ``None``.
    """
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.oficio_id == int(oficio_id),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _conclusion_label(resultado: str | None) -> str | None:
    if not resultado:
        return None
    key = str(resultado).strip().upper()
    return _CUMPLIMIENTO_LABEL.get(key, str(resultado).strip())


def _ruta_item_operativo_mas_reciente(ini: IniciadorRuta) -> RutaItem | None:
    return (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )


def _ruta_item_cierre_realizado(ini: IniciadorRuta) -> RutaItem | None:
    return (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
        )
        .order_by(RutaItem.id.desc())
        .first()
    )


def _actuacion_visita_desde_iniciador(
    ini: IniciadorRuta,
    *,
    actuacion_ancla_id: int,
) -> Actuaciones | None:
    item = _ruta_item_cierre_realizado(ini)
    if item is None or item.actuacion_id is None:
        return None
    if int(item.actuacion_id) == int(actuacion_ancla_id):
        return None
    return db.session.get(Actuaciones, int(item.actuacion_id))


def _orden_trabajo_numero_desde_item_o_act(
    item: RutaItem | None,
    act_visita: Actuaciones | None,
) -> str | None:
    if item is not None and item.orden_trabajo_id:
        ot = db.session.get(OrdenTrabajo, int(item.orden_trabajo_id))
        if ot is not None:
            num = getattr(ot, "numero_acta", None)
            if num is not None and str(num).strip():
                return str(num).strip()
    if act_visita is not None:
        grid = actuacion_to_grid_row(act_visita)
        ot_num = grid.get("orden_trabajo_numero")
        if ot_num is not None and str(ot_num).strip():
            return str(ot_num).strip()
    return None


def _payload_ejecucion_reinspeccion(
    act_visita: Actuaciones,
    *,
    ini_oficio: IniciadorRuta | None,
) -> Dict[str, Any]:
    grid_v = actuacion_to_grid_row(act_visita)
    resultado = getattr(act_visita, "resultado_cumplimiento_oficio", None)
    res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
    tipo_lab = None
    raw_tipo = grid_v.get("tipo_actuacion")
    if raw_tipo and str(raw_tipo).strip():
        tipo_lab = str(raw_tipo).strip()
    elif ini_oficio and ini_oficio.tipo_iniciador in (
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        try:
            tipo_lab = tipo_actuacion_para_iniciador(ini_oficio.tipo_iniciador)
        except KeyError:
            tipo_lab = None
    return {
        "actuacion_id": act_visita.id,
        "inspectores_texto": grid_v.get("inspectores_texto"),
        "inspector1": grid_v.get("inspector1"),
        "inspector2": grid_v.get("inspector2"),
        "inspector3": grid_v.get("inspector3"),
        "fecha_actuacion": grid_v.get("fecha_actuacion"),
        "orden_trabajo_numero": grid_v.get("orden_trabajo_numero"),
        "tipo_inspeccion_labrada": tipo_lab,
        "resultado_cumplimiento_oficio": res_val,
    }


def oficio_recorrido_campos_operativos(
    oficio: Oficio,
    *,
    actuacion_ancla_id: int | None = None,
) -> Dict[str, Any]:
    """
    OT, conclusión y ejecución de reinspección propios del oficio (no globales de la comprobación).

    Parámetros:
        oficio: oficio activo.
        actuacion_ancla_id: actuación con acta de comprobación (para distinguir visita de cierre).

    Retorno:
        Dict con ``iniciador_id``, ``estado_iniciador``, ``orden_trabajo``,
        ``resultado``, ``conclusion``, ``fecha_conclusion`` y ``ejecucion_reinspeccion`` (si aplica).
    """
    out: Dict[str, Any] = {
        "iniciador_id": None,
        "estado_iniciador": None,
        "orden_trabajo": None,
        "orden_trabajo_numero": None,
        "resultado": None,
        "resultado_cumplimiento_oficio": None,
        "conclusion": None,
        "fecha_conclusion": None,
        "ejecucion_reinspeccion": None,
    }
    ini = iniciador_reinspeccion_por_oficio(oficio.id)
    if ini is None:
        return out

    out["iniciador_id"] = ini.id
    out["estado_iniciador"] = ini.estado_iniciador

    ancla_id = actuacion_ancla_id or ini.actuacion_id
    item_cierre = _ruta_item_cierre_realizado(ini)
    item_operativo = item_cierre or _ruta_item_operativo_mas_reciente(ini)
    act_visita: Actuaciones | None = None

    if ancla_id is not None:
        act_visita = _actuacion_visita_desde_iniciador(ini, actuacion_ancla_id=int(ancla_id))

    ot_num = _orden_trabajo_numero_desde_item_o_act(item_operativo, act_visita)
    if ot_num:
        out["orden_trabajo"] = ot_num
        out["orden_trabajo_numero"] = ot_num

    if act_visita is not None:
        resultado = getattr(act_visita, "resultado_cumplimiento_oficio", None)
        res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
        res_str = str(res_val).strip() if res_val is not None else None
        out["resultado"] = res_str
        out["resultado_cumplimiento_oficio"] = res_str
        out["conclusion"] = _conclusion_label(res_str)
        if act_visita.fecha is not None:
            out["fecha_conclusion"] = act_visita.fecha.isoformat()
        out["ejecucion_reinspeccion"] = _payload_ejecucion_reinspeccion(act_visita, ini_oficio=ini)

    return out
