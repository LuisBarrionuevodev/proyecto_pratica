"""
Presentación para bandejas de Actas de comprobación (reinspección oficio / recorrido).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

from sqlalchemy import or_

from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    expediente_envio_por_comprobacion,
    oficio_por_comprobacion,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import Actuaciones, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio


def iniciador_reinspeccion_oficio_vigente(actuacion_id: int) -> Optional[IniciadorRuta]:
    """
    Último iniciador ``REINSPECCION_OFICIO`` no soft-deleted para la actuación.

    Parámetros:
        actuacion_id: PK de ``Actuaciones``.

    Retorno:
        ``IniciadorRuta`` o ``None`` si no hay iniciador activo de ese tipo.

    Errores:
        Ninguno (consulta de solo lectura).
    """
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == actuacion_id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _expediente_respuesta_oficio(comprobacion_id: int) -> Optional[Expediente]:
    """
    Expediente de respuesta vinculado a un oficio de la comprobación.

    Alineado a la bandeja de reinspección: admite ``tipo_expediente`` explícito o ``NULL`` (legado).
    """
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id)
        .filter(Expediente.oficio_id.isnot(None))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.desc())
        .first()
    )


def estado_recorrido_label(act: Actuaciones) -> str:
    """
    Etiqueta consultiva del estado del circuito documental para la fila de actuación.

    Orden del circuito: expediente de envío de acta → oficio administrativo → (re)programación
    de reinspección. Sin expediente de envío aún no corresponde mostrar «Esperando oficio».
    """
    if not act.comprobacion_id:
        return "—"
    exp_env = expediente_envio_por_comprobacion(act.comprobacion_id)
    if not exp_env:
        return "Esperando expediente"
    ofi = oficio_por_comprobacion(act.comprobacion_id)
    if not ofi:
        return "Esperando oficio"

    ini = iniciador_reinspeccion_oficio_vigente(act.id)
    if not ini:
        return "Oficio cargado — sin reinspección programada"
    if ini.estado_iniciador == "CUMPLIDO":
        return "Reinspección cumplida"
    if ini.estado_iniciador in inactive_estados():
        return f"Cerrado ({ini.estado_iniciador})"
    return "Pendiente reinspección por oficio"


def reinspeccion_oficio_bandeja_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
    iniciador: IniciadorRuta | None = None,
) -> Dict[str, Any]:
    """
    Fila JSON para la bandeja «Pendiente de reinspección» (circuito documental listo).

    Parámetros:
        act: actuación ancla (con comprobación).
        counts_by_eo: mapa opcional para ``actuacion_to_grid_row``.
        iniciador: si se pasa, se incluyen ``iniciador_id`` / estado / tipo (compat. tests y callers legacy).

    Retorno:
        dict alineado a ``IReinspeccionOficioPendienteRow`` (iniciador ausente → ``iniciador_id`` 0 y strings vacíos).

    Nota:
        Cuando ``iniciador`` es ``None``, corresponde al caso «oficio cargado — sin reinspección programada»
        (la bandeja operativa lista antes de crear ``REINSPECCION_OFICIO``).
    """
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    row: Dict[str, Any] = dict(base)
    if iniciador is not None:
        row["iniciador_id"] = iniciador.id
        row["estado_iniciador"] = iniciador.estado_iniciador
        row["tipo_iniciador"] = iniciador.tipo_iniciador
        row["fecha_origen_iniciador"] = (
            iniciador.fecha_origen.isoformat() if iniciador.fecha_origen else None
        )
    else:
        row["iniciador_id"] = 0
        row["estado_iniciador"] = ""
        row["tipo_iniciador"] = ""
        row["fecha_origen_iniciador"] = None
    row["documento_pendiente"] = "Reinspección por oficio"

    cid = getattr(act, "comprobacion_id", None)
    if cid:
        exp_env = expediente_envio_por_comprobacion(int(cid))
        if exp_env:
            row["expediente_envio_numero"] = getattr(exp_env, "numero_expediente", None)
            row["expediente_envio_anio"] = getattr(exp_env, "anio", None)
            fe = getattr(exp_env, "fecha_expediente", None)
            row["fecha_expediente_envio"] = fe.isoformat() if fe is not None else None
        ofi = oficio_por_comprobacion(int(cid))
        if ofi:
            row["oficio_numero"] = getattr(ofi, "numero_oficio", None)
            row["oficio_anio"] = getattr(ofi, "anio", None)
            fo = getattr(ofi, "fecha_oficio", None)
            row["fecha_oficio"] = fo.isoformat() if fo is not None else None
            row["juzgado_nombre"] = _juzgado_nombre(ofi)
        exp_resp = _expediente_respuesta_oficio(int(cid))
        if exp_resp:
            row["expediente_respuesta_numero"] = getattr(exp_resp, "numero_expediente", None)
            row["expediente_respuesta_anio"] = getattr(exp_resp, "anio", None)
            fr = getattr(exp_resp, "fecha_expediente", None)
            row["fecha_expediente_respuesta"] = fr.isoformat() if fr is not None else None

    ini_oficio = _iniciador_trabajo_oficio_mas_reciente(act.id)
    row["tipo_visita_resultado"] = _tipo_visita_resultado_final(base, ini_oficio)
    row["estado_recorrido"] = estado_recorrido_label(act)
    return row


def iniciador_reinspeccion_to_row(
    ini: IniciadorRuta,
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    """
    Fila para bandeja Pendientes de reinspección (oficio ya cargado).

    Incluye el mismo snapshot que ``actuacion_to_grid_row`` (contribuyente, domicilio, inspección,
    acta de comprobación, etc.) más los campos del iniciador y el detalle documental de envío /
    oficio / expediente de respuesta para modales alineados al circuito.

    Además (paridad con recorrido / grilla):
    - ``tipo_visita_resultado``: tipo de visita desambigüado (p. ej. verificar e informar) o ``None``.
    - ``estado_recorrido``: etiqueta de circuito documental (misma función que la tabla Recorrido).
    """
    return reinspeccion_oficio_bandeja_row(act, counts_by_eo=counts_by_eo, iniciador=ini)


def comprobacion_recorrido_resumen_row(
    act: Actuaciones,
    *,
    counts_by_eo: dict[int, int] | None = None,
) -> Dict[str, Any]:
    base = actuacion_to_grid_row(act, counts_by_eo=counts_by_eo)
    base["estado_recorrido"] = estado_recorrido_label(act)
    cid = getattr(act, "comprobacion_id", None)
    if cid:
        ofi = oficio_por_comprobacion(int(cid))
        if ofi:
            base["oficio_numero"] = getattr(ofi, "numero_oficio", None)
            base["oficio_anio"] = getattr(ofi, "anio", None)
            fo = getattr(ofi, "fecha_oficio", None)
            base["fecha_oficio"] = fo.isoformat() if fo is not None else None
            base["juzgado_nombre"] = _juzgado_nombre(ofi)
        exp_resp = _expediente_respuesta_oficio(int(cid))
        if exp_resp:
            base["expediente_respuesta_numero"] = getattr(exp_resp, "numero_expediente", None)
            base["expediente_respuesta_anio"] = getattr(exp_resp, "anio", None)
    return base


def _iniciador_origen_primera_actuacion(act: Actuaciones) -> Optional[IniciadorRuta]:
    """
    Iniciador mostrado en ``origen.iniciador`` del detalle de recorrido (solo lectura / UI).

    Debe reflejar el **origen de la actuación** donde se labró la primera comprobación
    (p. ej. DENUNCIA, RELEVAMIENTO), no el iniciador de **reinspección por oficio**
    (posterior en el circuito).

    Regla: entre los ``IniciadorRuta`` de esta actuación (no borrados), el de menor ``id``
    excluyendo ``REINSPECCION_OFICIO``. Si solo hubiera reinspección por oficio, se usa el
    de menor ``id`` (compatibilidad). No altera cómo se crean ni actualizan iniciadores en BD.
    """
    q_base = IniciadorRuta.query.filter(
        IniciadorRuta.actuacion_id == act.id,
        IniciadorRuta.deleted_at.is_(None),
    )
    primero_sin_reinsp_ofi = (
        q_base.filter(IniciadorRuta.tipo_iniciador != "REINSPECCION_OFICIO")
        .order_by(IniciadorRuta.id.asc())
        .first()
    )
    if primero_sin_reinsp_ofi is not None:
        return primero_sin_reinsp_ofi
    return q_base.order_by(IniciadorRuta.id.asc()).first()


_TIPOS_INI_TRABAJO_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)

_TIPOS_VISITA_CATALOG = frozenset(
    {
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
    }
)


def _norm_tipo_catalogo(s: str | None) -> str:
    if not s:
        return ""
    t = str(s).strip().upper().replace("_", " ")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def _iniciador_trabajo_oficio_mas_reciente(act_id: int) -> Optional[IniciadorRuta]:
    """Último iniciador de circuito oficio/reinspección (tipos operativos alineados a Completar trabajo)."""
    return (
        IniciadorRuta.query.filter(
            IniciadorRuta.actuacion_id == act_id,
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_INI_TRABAJO_OFICIO),
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )


def _tipo_visita_resultado_final(
    grid: Dict[str, Any],
    ini_oficio: Optional[IniciadorRuta],
) -> Optional[str]:
    """
    Actuación **resultante** del circuito oficio/reinspección (ratificación / verificar e informar).

    No devuelve ``REINSPECCION`` genérico: ese valor describe el paso/circuito, no la actuación hija.
    En ese caso se devuelve ``None`` y la UI muestra «Pendiente» hasta que ``act.tipo`` refleje
    el tipo concreto labrado.
    """
    raw = grid.get("tipo_actuacion")
    if raw and _norm_tipo_catalogo(str(raw)) in {_norm_tipo_catalogo(x) for x in _TIPOS_VISITA_CATALOG}:
        return str(raw).strip()

    if ini_oficio and ini_oficio.tipo_iniciador in (
        "VERIFICAR_INFORMAR_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
    ):
        try:
            return tipo_actuacion_para_iniciador(ini_oficio.tipo_iniciador)
        except KeyError:
            pass

    if raw and _norm_tipo_catalogo(str(raw)) == "REINSPECCION":
        return None

    if raw:
        return str(raw).strip()
    return None


def _juzgado_nombre(ofi: Optional[Oficio]) -> Optional[str]:
    if not ofi or not getattr(ofi, "juzgado_id", None):
        return None
    jz = JuzgadoCatalogo.query.filter_by(id=int(ofi.juzgado_id)).first()
    return getattr(jz, "nombre", None) if jz else None


def referencia_actuacion_from_grid_row(grid: Dict[str, Any]) -> Dict[str, Any]:
    """
    Snapshot de la actuación (misma fuente que ``actuacion_to_grid_row``).

    Reutilizable en detalle de recorrido (solo lectura) y en ficha documental operativa de comprobación.
    """
    return {
        "fecha_actuacion": grid.get("fecha_actuacion"),
        "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
        "calle": grid.get("calle_mostrar") or grid.get("calle"),
        "numero": grid.get("numero_mostrar") or grid.get("numero"),
        "contrib_apellido": grid.get("contrib_apellido"),
        "contrib_nombre": grid.get("contrib_nombre"),
        "razon_social": grid.get("razon_social"),
        "doc_nro": grid.get("doc_nro"),
        "rubro_nombre": grid.get("rubro_nombre"),
        "comprobacion_motivo": grid.get("comprobacion_motivo"),
        "acta_inspeccion_num": grid.get("acta_inspeccion_num"),
        "acta_comprobacion_num": grid.get("acta_comprobacion_num"),
        "inspectores_texto": grid.get("inspectores_texto"),
        "inspector1": grid.get("inspector1"),
        "inspector2": grid.get("inspector2"),
        "inspector3": grid.get("inspector3"),
        "tipo_actuacion": grid.get("tipo_actuacion"),
    }


def comprobacion_recorrido_detalle(act: Actuaciones) -> Dict[str, Any]:
    """
    Detalle estructurado consultivo (sin PDF): origen, comprobación, expedientes, oficio, reinspección, resultado.

    Contrato estable (extensiones UI recorrido):
    - ``referencia_actuacion``: mismos hechos de visita que la grilla (domicilio mostrable, titular,
      documento, rubro, inspectores, tipo de actuación, acta de inspección) para que el modal no
      dependa del listado.
    - ``origen.iniciador``: iniciador de origen de la actuación / primera comprobación
      (excluye ``REINSPECCION_OFICIO`` salvo si es el único).
    - ``oficio``: incluye ``causa``, ``juzgado_id``, ``juzgado_nombre`` cuando hay oficio.
    - ``resultado_final.tipo_actuacion``: mismo string que la grilla (``actuacion_to_grid_row``).
    - ``resultado_final.tipo_visita``: actuación resultante (ratificación / verificar e informar) o
      ``None`` si aún no hay tipo concreto (p. ej. ``REINSPECCION`` genérico en ``act.tipo``).
    - ``reinspeccion_por_oficio``: metadatos del iniciador ``REINSPECCION_OFICIO`` (id, tipo, estado,
      fecha de origen, documento). Si el trámite está ``CUMPLIDO``, ``ejecucion_reinspeccion`` resume
      la visita ya labrada (inspectores, fecha, OT, tipo de inspección y cumplimiento) desde el mismo
      snapshot de grilla de la actuación ancla (misma fila ORM actualizada al cerrar).
    """
    if not act.comprobacion_id:
        raise ValueError("La actuación no tiene comprobación")

    grid = actuacion_to_grid_row(act)
    ini_oficio = _iniciador_trabajo_oficio_mas_reciente(act.id)
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

    ini_origen = _iniciador_origen_primera_actuacion(act)
    iniciador_payload: Optional[Dict[str, Any]] = None
    if ini_origen is not None:
        iniciador_payload = {
            "tipo_iniciador": ini_origen.tipo_iniciador,
            "estado_iniciador": ini_origen.estado_iniciador,
            "fecha_origen": ini_origen.fecha_origen.isoformat() if ini_origen.fecha_origen else None,
        }

    resultado = getattr(act, "resultado_cumplimiento_oficio", None)
    res_val = resultado.value if resultado is not None and hasattr(resultado, "value") else resultado
    tipo_visita_final = _tipo_visita_resultado_final(grid, ini_oficio)

    oficio_payload: Optional[Dict[str, Any]] = None
    if ofi is not None:
        oficio_payload = {
            "id": ofi.id,
            "numero_oficio": ofi.numero_oficio,
            "anio": ofi.anio,
            "fecha_oficio": ofi.fecha_oficio.isoformat() if ofi.fecha_oficio else None,
            "causa": getattr(ofi, "causa", None),
            "juzgado_id": getattr(ofi, "juzgado_id", None),
            "juzgado_nombre": _juzgado_nombre(ofi),
        }

    return {
        "actuacion_id": act.id,
        "origen": {
            "descripcion": "Actuación con acta de comprobación",
            "fecha_actuacion": grid.get("fecha_actuacion"),
            "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
            "iniciador": iniciador_payload,
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
        "oficio": oficio_payload,
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
                "tipo_iniciador": ini.tipo_iniciador,
                "estado_iniciador": ini.estado_iniciador,
                "fecha_origen": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
                "documento_pendiente": "Reinspección por oficio",
                "ejecucion_reinspeccion": (
                    {
                        "inspectores_texto": grid.get("inspectores_texto"),
                        "inspector1": grid.get("inspector1"),
                        "inspector2": grid.get("inspector2"),
                        "inspector3": grid.get("inspector3"),
                        "fecha_actuacion": grid.get("fecha_actuacion"),
                        "orden_trabajo_numero": grid.get("orden_trabajo_numero"),
                        "tipo_inspeccion_labrada": tipo_visita_final
                        or (
                            str(grid.get("tipo_actuacion")).strip()
                            if grid.get("tipo_actuacion")
                            else None
                        ),
                        "resultado_cumplimiento_oficio": res_val,
                    }
                    if ini.estado_iniciador == "CUMPLIDO"
                    else None
                ),
            }
            if ini
            else None
        ),
        "referencia_actuacion": referencia_actuacion_from_grid_row(grid),
        "resultado_final": {
            "resultado_cumplimiento_oficio": res_val,
            "estado_recorrido": estado_recorrido_label(act),
            "tipo_actuacion": grid.get("tipo_actuacion"),
            "tipo_visita": tipo_visita_final,
        },
    }
