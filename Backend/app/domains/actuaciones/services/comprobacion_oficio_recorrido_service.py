"""
Campos operativos de recorrido por oficio (OT, conclusión, ejecución de reinspección).

Un oficio puede tener su propio iniciador ``REINSPECCION_OFICIO``, ruta item y actuación de cierre.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import Actuaciones, IniciadorRuta, Oficio, OrdenTrabajo, RutaItem, RutaTrabajo

TIPOS_INI_TRABAJO_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

_CUMPLIMIENTO_LABEL = {
    "CUMPLE": "Cumple",
    "NO_CUMPLE": "No cumple",
}

_TIPO_INICIADOR_VISITA_LABEL = {
    "REINSPECCION_OFICIO": "Reinspección",
    "VERIFICAR_INFORMAR_OFICIO": "Verificar e informar",
    "RATIFICACION_CLAUSURA_OFICIO": "Ratificación de clausura",
    "RATIFICACION_DECOMISO_OFICIO": "Ratificación de decomiso",
}

_MOTIVO_NO_REALIZADO_LABEL = {
    "LOCAL_CERRADO": "Local cerrado",
    "INCLEMENCIA_TIEMPO": "Inclemencia tiempo",
    "NO_EXISTE_LOCAL": "No existe local",
    "OTRO": "Otro",
}

_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")


def iniciador_reinspeccion_por_oficio(oficio_id: int) -> IniciadorRuta | None:
    """
    Último iniciador de circuito oficio/reinspección vinculado al oficio (excluye soft-deleted).

    Incluye tipos promovidos tras Completar trabajo (``VERIFICAR_INFORMAR_OFICIO``, ratificaciones).

    Parámetros:
        oficio_id: PK de ``Oficio``.

    Retorno:
        ``IniciadorRuta`` o ``None``.
    """
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.oficio_id == int(oficio_id),
            IniciadorRuta.tipo_iniciador.in_(TIPOS_INI_TRABAJO_OFICIO),
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def iniciador_trabajo_por_actuacion(actuacion_id: int) -> IniciadorRuta | None:
    """
    Último iniciador de circuito oficio/reinspección para la actuación ancla.

    Parámetros:
        actuacion_id: PK de ``Actuaciones``.

    Retorno:
        ``IniciadorRuta`` o ``None``.
    """
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == int(actuacion_id),
            IniciadorRuta.tipo_iniciador.in_(TIPOS_INI_TRABAJO_OFICIO),
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _oficio_compact_label(numero: Any, anio: Any) -> str:
    n = (str(numero).strip() if numero is not None else "")
    a = (str(anio).strip() if anio is not None else "")
    if not n and not a:
        return ""
    return "/".join(p for p in (n, a) if p)


def _motivo_no_realizado_label(motivo: str | None) -> str | None:
    if not motivo:
        return None
    key = str(motivo).strip().upper()
    return _MOTIVO_NO_REALIZADO_LABEL.get(key, str(motivo).strip().replace("_", " ").title())


def _tipo_visita_oficio_label(
    ini: IniciadorRuta | None,
    ejecucion: Dict[str, Any] | None,
) -> str | None:
    if ini is not None:
        mapped = _TIPO_INICIADOR_VISITA_LABEL.get(str(ini.tipo_iniciador or "").strip())
        if mapped:
            return mapped
        if ini.tipo_iniciador in (
            "VERIFICAR_INFORMAR_OFICIO",
            "RATIFICACION_CLAUSURA_OFICIO",
            "RATIFICACION_DECOMISO_OFICIO",
        ):
            try:
                return tipo_actuacion_para_iniciador(ini.tipo_iniciador)
            except KeyError:
                pass
    if ejecucion:
        tipo_lab = (ejecucion.get("tipo_inspeccion_labrada") or "").strip()
        if tipo_lab:
            key = tipo_lab.upper().replace("_", " ")
            catalog = {
                "VERIFICAR E INFORMAR": "Verificar e informar",
                "RATIFICACION DE CLAUSURA": "Ratificación de clausura",
                "RATIFICACION DE DECOMISO": "Ratificación de decomiso",
                "REINSPECCION": "Reinspección",
            }
            return catalog.get(key, tipo_lab.title())
    return None


def _visita_resumen_texto(
    *,
    oficio_texto: str | None,
    ini: IniciadorRuta | None,
    item: RutaItem | None,
    act_visita: Actuaciones | None,
    ejecucion: Dict[str, Any] | None,
) -> str:
    """Línea compacta para columna Recorrido: ``Oficio 432/2026 · Verificar e informar · Realizada``."""
    head = f"Oficio {oficio_texto}" if oficio_texto else "Oficio —"
    if ini is None:
        return f"{head} · Sin inspección programada"

    if item is not None and item.estado_ruta_item in _ESTADOS_RUTA_ITEM_ABIERTOS:
        ruta = db.session.get(RutaTrabajo, int(item.ruta_trabajo_id))
        if ruta is not None:
            if ruta.estado_ruta in ("PUBLICADA", "EN_CURSO"):
                return f"{head} · En curso"
            if ruta.estado_ruta == "BORRADOR":
                return f"{head} · Pendiente de planificación"

    estado_ejec = (item.estado_ejecucion or "").strip().upper() if item is not None else ""
    if estado_ejec == "NO_REALIZADO":
        motivo = _motivo_no_realizado_label(
            getattr(item, "motivo_no_realizado", None) if item is not None else None
        )
        if motivo:
            return f"{head} · No realizada · {motivo}"
        return f"{head} · No realizada"

    if ini.estado_iniciador == "CUMPLIDO" or act_visita is not None or estado_ejec == "REALIZADO":
        tipo = _tipo_visita_oficio_label(ini, ejecucion)
        if tipo:
            return f"{head} · {tipo} · Realizada"
        return f"{head} · Realizada"

    if (ini.estado_iniciador or "").upper() == "PENDIENTE":
        return f"{head} · Pendiente reinspección"

    estado = (ini.estado_iniciador or "").strip()
    return f"{head} · {estado}" if estado else head


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
        "tipo_iniciador": None,
        "estado_ejecucion": None,
        "motivo_no_realizado": None,
        "orden_trabajo": None,
        "orden_trabajo_numero": None,
        "resultado": None,
        "resultado_cumplimiento_oficio": None,
        "conclusion": None,
        "fecha_conclusion": None,
        "ejecucion_reinspeccion": None,
        "visita_resumen_texto": None,
    }
    ini = iniciador_reinspeccion_por_oficio(oficio.id)
    if ini is None:
        return out

    out["iniciador_id"] = ini.id
    out["estado_iniciador"] = ini.estado_iniciador
    out["tipo_iniciador"] = ini.tipo_iniciador

    ancla_id = actuacion_ancla_id or ini.actuacion_id
    item_cierre = _ruta_item_cierre_realizado(ini)
    item_operativo = item_cierre or _ruta_item_operativo_mas_reciente(ini)
    act_visita: Actuaciones | None = None

    if item_operativo is not None:
        out["estado_ejecucion"] = item_operativo.estado_ejecucion
        out["motivo_no_realizado"] = getattr(item_operativo, "motivo_no_realizado", None)

    if ancla_id is not None:
        act_visita = _actuacion_visita_desde_iniciador(ini, actuacion_ancla_id=int(ancla_id))

    ot_num = _orden_trabajo_numero_desde_item_o_act(item_operativo, act_visita)
    if ot_num:
        out["orden_trabajo"] = ot_num
        out["orden_trabajo_numero"] = ot_num

    ejecucion: Dict[str, Any] | None = None
    if act_visita is not None:
        resultado = getattr(act_visita, "resultado_cumplimiento_oficio", None)
        res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
        res_str = str(res_val).strip() if res_val is not None else None
        out["resultado"] = res_str
        out["resultado_cumplimiento_oficio"] = res_str
        out["conclusion"] = _conclusion_label(res_str)
        if act_visita.fecha is not None:
            out["fecha_conclusion"] = act_visita.fecha.isoformat()
        ejecucion = _payload_ejecucion_reinspeccion(act_visita, ini_oficio=ini)
        out["ejecucion_reinspeccion"] = ejecucion

    oficio_texto = _oficio_compact_label(
        getattr(oficio, "numero_oficio", None),
        getattr(oficio, "anio", None),
    ) or None
    out["visita_resumen_texto"] = _visita_resumen_texto(
        oficio_texto=oficio_texto,
        ini=ini,
        item=item_operativo,
        act_visita=act_visita,
        ejecucion=ejecucion,
    )

    return out
