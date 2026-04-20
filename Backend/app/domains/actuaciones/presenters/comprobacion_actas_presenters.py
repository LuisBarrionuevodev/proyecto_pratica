"""
Presentación para bandejas de Actas de comprobación (reinspección oficio / recorrido).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

from app.domains.actuaciones.presenters.actuacion_presenters import (
    actuacion_to_grid_row,
    expediente_envio_por_comprobacion,
    oficio_por_comprobacion,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import inactive_estados
from app.domains.rutas_trabajo.services.ruta_publicar_service import tipo_actuacion_para_iniciador
from app.models import Actuaciones, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio


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


def comprobacion_recorrido_detalle(act: Actuaciones) -> Dict[str, Any]:
    """
    Detalle estructurado consultivo (sin PDF): origen, comprobación, expedientes, oficio, reinspección, resultado.

    Contrato estable (extensiones UI recorrido):
    - ``origen.iniciador``: iniciador de origen de la actuación / primera comprobación
      (excluye ``REINSPECCION_OFICIO`` salvo si es el único).
    - ``oficio``: incluye ``causa``, ``juzgado_id``, ``juzgado_nombre`` cuando hay oficio.
    - ``resultado_final.tipo_actuacion``: mismo string que la grilla (``actuacion_to_grid_row``).
    - ``resultado_final.tipo_visita``: actuación resultante (ratificación / verificar e informar) o
      ``None`` si aún no hay tipo concreto (p. ej. ``REINSPECCION`` genérico en ``act.tipo``).
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
                "estado_iniciador": ini.estado_iniciador,
                "fecha_origen": ini.fecha_origen.isoformat() if ini.fecha_origen else None,
            }
            if ini
            else None
        ),
        "resultado_final": {
            "resultado_cumplimiento_oficio": res_val,
            "estado_recorrido": estado_recorrido_label(act),
            "tipo_actuacion": grid.get("tipo_actuacion"),
            "tipo_visita": _tipo_visita_resultado_final(grid, ini_oficio),
        },
    }
