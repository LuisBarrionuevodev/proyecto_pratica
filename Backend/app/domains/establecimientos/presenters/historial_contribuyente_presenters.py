"""
Presenter de filas de historial por DNI/CUIT (Establecimientos — solo lectura).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.domains.actuaciones.presenters.actuacion_presenters import (
    ActuacionGridBatchMaps,
    build_actuacion_grid_batch_maps,
    build_iniciador_ruta_por_actuacion_id,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    HistorialContribuyenteEntry,
)
from app.domains.rutas_trabajo.utils.rubro_operativo import (
    rubro_nombre_operativo_para_iniciador,
    titular_operativo_visible_para_iniciador,
)
from app.models import Actuaciones, Expediente, Oficio, RutaItem


def _enum_or_str(val: Any) -> str | None:
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    s = str(val).strip()
    return s or None


def _domicilio_texto(act: Actuaciones | None, ruta_item: RutaItem | None) -> str | None:
    dom = None
    if act is not None and act.domicilio:
        dom = act.domicilio
    elif ruta_item and ruta_item.iniciador_ruta and ruta_item.iniciador_ruta.domicilio:
        dom = ruta_item.iniciador_ruta.domicilio
    if dom is None:
        return None
    calle = (dom.calle or "").strip()
    numero = (dom.numero or "").strip()
    if calle and numero:
        return f"{calle} {numero}"
    return calle or numero or None


def _inspectores_texto(act: Actuaciones | None) -> str | None:
    if act is None:
        return None
    insp_list = getattr(act, "inspector", None) or []
    nombres = []
    for i in sorted(insp_list, key=lambda x: getattr(x, "id", 0)):
        n = getattr(i, "nombre", None)
        if n:
            nombres.append(str(n).strip())
    return ", ".join(nombres) if nombres else None


def _resolve_tramites(
    act: Actuaciones | None,
    iniciador: Any,
    batch: ActuacionGridBatchMaps | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resuelve expediente/oficio asociados a la actuación o iniciador."""
    tramites: dict[str, Any] = {"expediente": None, "oficio": None}
    expediente: Expediente | None = None
    oficio: Oficio | None = None

    if act is not None:
        if act.notificacion_id and batch is not None:
            expediente = batch.expediente_primero_by_notif_id.get(int(act.notificacion_id))
        if act.comprobacion_id and batch is not None:
            expediente = expediente or batch.expediente_envio_by_comp_id.get(int(act.comprobacion_id))
            comp = act.comprobacion
            if comp and getattr(comp, "oficio", None):
                ofi_rel = comp.oficio
                if isinstance(ofi_rel, list):
                    oficio = ofi_rel[0] if ofi_rel else None
                else:
                    oficio = ofi_rel

    if iniciador is not None:
        if iniciador.oficio_id and iniciador.oficio:
            oficio = iniciador.oficio
        if (
            iniciador.comprobacion_id
            and iniciador.oficio_id
            and batch is not None
        ):
            expediente = batch.expediente_respuesta_by_pair.get(
                (int(iniciador.comprobacion_id), int(iniciador.oficio_id))
            ) or expediente

    if expediente is not None:
        anio_exp = int(expediente.anio) if expediente.anio is not None else None
        exp_block = _acta_block(expediente.numero_expediente, anio_exp)
        tramites["expediente"] = {
            "id": expediente.id,
            "numero": expediente.numero_expediente,
            "anio": anio_exp,
            "tipo": _enum_or_str(expediente.tipo_expediente),
            "texto": exp_block["texto"] if exp_block else None,
        }
    if oficio is not None:
        ofi_block = _acta_block(oficio.numero_oficio, oficio.anio)
        tramites["oficio"] = {
            "id": oficio.id,
            "numero": oficio.numero_oficio,
            "anio": oficio.anio,
            "texto": ofi_block["texto"] if ofi_block else None,
        }

    return tramites, {"expediente": expediente, "oficio": oficio}


def _acta_block(numero: Any, anio: Any) -> dict[str, Any] | None:
    """Bloque de acta/trámite con número, año y texto listo para UI."""
    if numero is None or not str(numero).strip():
        return None
    n = str(numero).strip()
    anio_val = int(anio) if anio is not None else None
    texto = f"{n}/{anio_val}" if anio_val is not None else n
    return {"numero": n, "anio": anio_val, "texto": texto}


def _build_actas(act: Actuaciones | None, iniciador: Any = None) -> dict[str, Any]:
    actas: dict[str, Any] = {
        "inspeccion": None,
        "notificacion": None,
        "comprobacion": None,
        "clausura": None,
        "decomiso": None,
    }
    if act is None:
        return actas

    ins = getattr(act, "inspeccion", None)
    if ins and getattr(ins, "numero_acta", None):
        actas["inspeccion"] = _acta_block(ins.numero_acta, getattr(ins, "anio", None))

    noti = getattr(act, "notificacion", None)
    if noti and getattr(noti, "numero_acta", None):
        actas["notificacion"] = _acta_block(noti.numero_acta, getattr(noti, "anio", None))

    comp = getattr(act, "comprobacion", None)
    if comp and getattr(comp, "numero_acta", None):
        actas["comprobacion"] = _acta_block(comp.numero_acta, getattr(comp, "anio", None))

    cla = getattr(act, "clausura", None)
    if cla and getattr(cla, "numero_acta", None):
        actas["clausura"] = _acta_block(cla.numero_acta, getattr(cla, "anio", None))

    dec = getattr(act, "decomiso", None)
    if dec and getattr(dec, "numero_acta", None):
        actas["decomiso"] = _acta_block(dec.numero_acta, getattr(dec, "anio", None))

    if (
        actas["notificacion"] is None
        and iniciador is not None
        and (iniciador.tipo_iniciador or "").strip() == "REINSPECCION_NOTIFICACION"
    ):
        noti_ini = getattr(iniciador, "notificacion", None)
        if noti_ini and getattr(noti_ini, "numero_acta", None):
            actas["notificacion"] = _acta_block(
                noti_ini.numero_acta,
                getattr(noti_ini, "anio", None),
            )

    return actas


def _format_actas_tramites_texto(actas: dict[str, Any], tramites: dict[str, Any]) -> str:
    """Texto compacto: Insp. · Notif. · Comp. · Claus. · Decom. · Exp. · Oficio."""
    parts: list[str] = []
    labels = [
        ("inspeccion", "Insp."),
        ("notificacion", "Notif."),
        ("comprobacion", "Comp."),
        ("clausura", "Claus."),
        ("decomiso", "Decom."),
    ]
    for key, label in labels:
        block = actas.get(key)
        if block and block.get("texto"):
            parts.append(f"{label} {block['texto']}")

    exp = tramites.get("expediente")
    if exp and exp.get("texto"):
        parts.append(f"Exp. {exp['texto']}")

    ofi = tramites.get("oficio")
    if ofi and ofi.get("texto"):
        parts.append(f"Oficio {ofi['texto']}")

    return " · ".join(parts)


def build_actas_tramites_payload_for_actuacion(
    act: Actuaciones,
    *,
    iniciador: Any = None,
    batch: ActuacionGridBatchMaps | None = None,
) -> dict[str, Any]:
    """
    Bloques ``actas``, ``tramites`` y texto compacto para historiales de solo lectura.

    Parámetros:
        act: actuación con relaciones de actas cargadas.
        iniciador: iniciador de ruta opcional (reinspección notificación).
        batch: mapas batch de expedientes/oficios.

    Retorno:
        dict con ``actas``, ``tramites`` y ``actas_tramites_texto``.
    """
    actas = _build_actas(act, iniciador)
    tramites, _ = _resolve_tramites(act, iniciador, batch)
    return {
        "actas": actas,
        "tramites": tramites,
        "actas_tramites_texto": _format_actas_tramites_texto(actas, tramites) or None,
    }


def _presentacion_estado(
    act: Actuaciones | None,
    ruta_item: RutaItem | None,
) -> tuple[str, bool | None]:
    """
    Estado de presentación (no modifica estados reales).

    Retorno:
        (estado, realizada) donde realizada es True/False/None.
    """
    if ruta_item is not None:
        estado_item = (ruta_item.estado_ruta_item or "").strip().upper()
        ejec = (ruta_item.estado_ejecucion or "").strip().upper() if ruta_item.estado_ejecucion else None
        if estado_item == "FINALIZADO":
            if ejec == "NO_REALIZADO":
                return "NO_REALIZADA", False
            if ejec == "REALIZADO":
                return "REALIZADA", True
        if estado_item in ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO"):
            return "PENDIENTE", None
        if estado_item == "NO_REALIZADO":
            return "NO_REALIZADA", False

    if act is None:
        return "PENDIENTE", None

    return "REALIZADA", True


def _tipo_actuacion(act: Actuaciones | None, iniciador: Any) -> str | None:
    if act is not None and act.tipo:
        return _enum_or_str(act.tipo)
    if iniciador is not None:
        tipo_ini = (iniciador.tipo_iniciador or "").strip()
        mapping = {
            "RELEVAMIENTO": "RELEVAMIENTO",
            "DENUNCIA": "DENUNCIA",
            "REINSPECCION_NOTIFICACION": "REINSPECCION",
            "REINSPECCION_OFICIO": "REINSPECCION",
            "VERIFICAR_INFORMAR_OFICIO": "VERIFICAR E INFORMAR",
            "RATIFICACION_CLAUSURA_OFICIO": "RATIFICACION DE CLAUSURA",
            "RATIFICACION_DECOMISO_OFICIO": "RATIFICACION DE DECOMISO",
        }
        return mapping.get(tipo_ini, tipo_ini or None)
    return None


def _observaciones(act: Actuaciones | None, ruta_item: RutaItem | None, iniciador: Any) -> str | None:
    if ruta_item and ruta_item.observaciones_ejecucion:
        return str(ruta_item.observaciones_ejecucion).strip() or None
    if iniciador and iniciador.observaciones:
        return str(iniciador.observaciones).strip() or None
    return None


def inspectores_historial_texto(act: Actuaciones | None) -> str | None:
    """Nombres de inspectores concatenados para historiales de solo lectura."""
    return _inspectores_texto(act)


def contraproducencia_historial_visible(
    act: Actuaciones | None,
    ruta_item: RutaItem | None,
) -> str | None:
    """
    Contraproducencia visible en historiales de solo lectura.

    Prioriza ``act.contraproducencia``; si no hay, deriva desde ``ruta_item.motivo_no_realizado``.
    """
    return _contraproducencia(act, ruta_item)


def _contraproducencia(act: Actuaciones | None, ruta_item: RutaItem | None) -> str | None:
    if act is not None and act.contraproducencia:
        return _enum_or_str(act.contraproducencia)
    if ruta_item is not None and ruta_item.motivo_no_realizado:
        motivo = _enum_or_str(ruta_item.motivo_no_realizado)
        mapping = {
            "LOCAL_CERRADO": "LOCAL CERRADO",
            "INCLEMENCIA_TIEMPO": "CLIMA",
            "NO_EXISTE_LOCAL": "NO EXISTE LOCAL",
            "OTRO": "OTROS",
        }
        return mapping.get(motivo or "", motivo)
    return None


def historial_contribuyente_row(
    entry: HistorialContribuyenteEntry,
    *,
    batch: ActuacionGridBatchMaps | None = None,
) -> dict[str, Any]:
    """
    Serializa una fila de historial por contribuyente.

    Parámetros:
        entry: fila interna del service.
        batch: mapas precargados de expedientes (evita N+1).

    Retorno:
        dict JSON con campos de ``HistorialContribuyenteRow``.
    """
    act = entry.act
    ruta_item = entry.ruta_item
    ini = entry.iniciador

    dom = act.domicilio if act is not None else None
    if dom is None and ini is not None:
        dom = ini.domicilio

    rubro_nombre = rubro_nombre_operativo_para_iniciador(ini, dom, act=act)

    estado, realizada = _presentacion_estado(act, ruta_item)
    actas = _build_actas(act, ini)
    tramites, refs = _resolve_tramites(act, ini, batch)
    actas_tramites_texto = _format_actas_tramites_texto(actas, tramites)

    ot_num = None
    if act is not None and act.orden_trabajo:
        ot_num = act.orden_trabajo.numero_acta or getattr(act.orden_trabajo, "numero", None)
    elif ruta_item is not None and ruta_item.orden_trabajo:
        ot_num = ruta_item.orden_trabajo.numero_acta

    row_id = act.id if act is not None else (ruta_item.id if ruta_item else None)

    titular_visible = titular_operativo_visible_para_iniciador(ini, act=act)
    if ini and ini.tipo_iniciador in ("RELEVAMIENTO", "DENUNCIA"):
        if act is None:
            titular_visible = False
        elif ruta_item is not None and (ruta_item.estado_ejecucion or "").strip().upper() != "REALIZADO":
            titular_visible = False

    return {
        "id": row_id,
        "fecha": entry.fecha_efectiva.isoformat() if entry.fecha_efectiva != date.min else None,
        "tipo_actuacion": _tipo_actuacion(act, ini),
        "estado": estado,
        "realizada": realizada,
        "domicilio_texto": _domicilio_texto(act, ruta_item),
        "rubro_nombre": rubro_nombre,
        "orden_trabajo_numero": ot_num,
        "inspectores_texto": _inspectores_texto(act),
        "contraproducencia": _contraproducencia(act, ruta_item),
        "observaciones": _observaciones(act, ruta_item, ini),
        "actas_tramites_texto": actas_tramites_texto or None,
        "actas": actas,
        "tramites": tramites,
        "actuacion_id": act.id if act is not None else None,
        "iniciador_id": ini.id if ini is not None else None,
        "ruta_item_id": ruta_item.id if ruta_item is not None else None,
        "oficio_id": (refs["oficio"].id if refs.get("oficio") else None),
        "expediente_id": (refs["expediente"].id if refs.get("expediente") else None),
        "origen": entry.origen,
        "titular_visible": titular_visible,
    }


def historial_contribuyente_rows(
    entries: list[HistorialContribuyenteEntry],
) -> list[dict[str, Any]]:
    """
    Presenta un lote de filas con mapas batch compartidos.

    Parámetros:
        entries: filas del service.

    Retorno:
        Lista de dicts listos para JSON.
    """
    acts = [e.act for e in entries if e.act is not None]
    act_ids = [int(a.id) for a in acts if a.id is not None]
    ini_map = build_iniciador_ruta_por_actuacion_id(act_ids)
    batch = build_actuacion_grid_batch_maps(acts, ini_map) if acts else None

    rows = []
    for entry in entries:
        entry_batch = batch
        if entry.act is None:
            entry_batch = None
        rows.append(historial_contribuyente_row(entry, batch=entry_batch))
    return rows
