"""
Modo de identidad operativa para Completar trabajo → Verificar e informar → Nueva inspección.

Distingue origen histórico incompleto (COMPLETE_HISTORICAL) de origen normal completo
(COMPLETE_EXISTING) usando la actuación origen del iniciador (``ini.actuacion_id``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from app.domains.actuaciones.utils.titular_actuacion_resolver import resolve_titular_grid_fields
from app.domains.rutas_trabajo.utils.rubro_operativo import rubro_nombre_operativo_para_iniciador
from app.models import Actuaciones, IniciadorRuta


COMPLETE_HISTORICAL = "COMPLETE_HISTORICAL"
COMPLETE_EXISTING = "COMPLETE_EXISTING"


class IdentidadAutoridad(TypedDict, total=False):
    """Snapshot de identidad formal autorizada desde actuación origen."""

    doc_nro: Optional[str]
    contrib_apellido: Optional[str]
    contrib_nombre: Optional[str]
    razon_social: Optional[str]
    rubro_nombre: Optional[str]
    calle: Optional[str]
    numero: Optional[str]


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def cargar_actuacion_origen(ini: IniciadorRuta | None) -> Actuaciones | None:
    """
    Carga la actuación origen referenciada por el iniciador.

    Parámetros:
        ini: iniciador del ítem de ruta.

    Retorno:
        Actuación origen o None si no hay ``actuacion_id``.
    """
    if ini is None or not ini.actuacion_id:
        return None
    return Actuaciones.query.get(int(ini.actuacion_id))


def _titular_snapshot_presente(act: Actuaciones) -> bool:
    has_persona = bool(
        _clean_str(getattr(act, "titular_nombre_historico", None))
        and _clean_str(getattr(act, "titular_apellido_historico", None))
    )
    has_razon = bool(_clean_str(getattr(act, "titular_razon_social_historica", None)))
    return has_persona or has_razon


def _contribuyente_formal_con_documento(act: Actuaciones) -> bool:
    dom = getattr(act, "domicilio", None)
    if dom is None:
        return False
    contrib = getattr(dom, "contribuyente", None)
    if contrib is None:
        return False
    doc = getattr(contrib, "documento", None) or getattr(contrib, "doc_nro", None)
    return bool(doc and str(doc).strip())


def _rubro_formal_en_act(act: Actuaciones) -> bool:
    dom = getattr(act, "domicilio", None)
    if dom is None:
        return False
    rub = getattr(dom, "rubro", None)
    if rub is not None and _clean_str(getattr(rub, "nombre", None)):
        return True
    return dom.rubro_id is not None


def resolver_modo_identidad_operativa(
    ini: IniciadorRuta | None,
    act_trabajo: Actuaciones | None = None,
) -> str:
    """
    Determina el modo de identidad para Verificar e informar con nueva inspección.

    Parámetros:
        ini: iniciador del ítem de ruta.
        act_trabajo: actuación de trabajo publicada (no se usa ``carga_solo_comprobacion`` de esta fila).

    Retorno:
        ``COMPLETE_HISTORICAL`` o ``COMPLETE_EXISTING``.

    Errores:
        ValueError: si no hay actuación origen y no puede inferirse el modo.
    """
    origin = cargar_actuacion_origen(ini)
    if origin is None:
        if act_trabajo is not None and _contribuyente_formal_con_documento(act_trabajo) and _rubro_formal_en_act(act_trabajo):
            return COMPLETE_EXISTING
        raise ValueError("No se pudo resolver la actuación origen para identidad operativa.")

    if _contribuyente_formal_con_documento(origin) and _rubro_formal_en_act(origin):
        return COMPLETE_EXISTING

    if bool(getattr(origin, "carga_solo_comprobacion", False)) and _titular_snapshot_presente(origin):
        if not _contribuyente_formal_con_documento(origin):
            return COMPLETE_HISTORICAL

    if _contribuyente_formal_con_documento(origin):
        return COMPLETE_EXISTING

    raise ValueError(
        "La actuación origen no tiene identidad formal completa ni califica como histórica incompleta."
    )


def identidad_autoridad_desde_origen(
    ini: IniciadorRuta | None,
    act_trabajo: Actuaciones | None = None,
) -> IdentidadAutoridad:
    """
    Extrae identidad formal autorizada desde la actuación origen.

    Parámetros:
        ini: iniciador con ``actuacion_id``.
        act_trabajo: actuación de ruta usada como fallback si no hay ``actuacion_id``.

    Retorno:
        Dict con titular, documento, rubro y domicilio de referencia.

    Errores:
        ValueError: si falta origen o identidad formal incompleta.
    """
    origin = cargar_actuacion_origen(ini)
    act_ref = origin if origin is not None else act_trabajo
    if act_ref is None:
        raise ValueError("Actuación origen no encontrada.")

    titular = resolve_titular_grid_fields(act_ref)
    dom = getattr(act_ref, "domicilio", None)
    rubro = rubro_nombre_operativo_para_iniciador(ini, dom, act=act_ref)
    if not rubro and dom and dom.rubro:
        rubro = _clean_str(dom.rubro.nombre)

    doc = _clean_str(titular.get("doc_nro"))
    if not doc:
        raise ValueError("La actuación origen no tiene documento formal.")

    if not rubro:
        raise ValueError("La actuación origen no tiene rubro formal.")

    return {
        "doc_nro": doc,
        "contrib_apellido": _clean_str(titular.get("contrib_apellido")),
        "contrib_nombre": _clean_str(titular.get("contrib_nombre")),
        "razon_social": _clean_str(titular.get("razon_social")),
        "rubro_nombre": rubro,
        "calle": _clean_str(getattr(dom, "calle", None)) if dom else None,
        "numero": _clean_str(getattr(dom, "numero", None)) if dom else None,
    }


def prefill_identidad_verificar_informar(
    ini: IniciadorRuta | None,
    act_trabajo: Actuaciones,
) -> Dict[str, Any]:
    """
    Arma prefill de identidad y ``identity_mode`` para presenter Completar trabajo.

    Parámetros:
        ini: iniciador del ítem.
        act_trabajo: actuación de ruta en curso.

    Retorno:
        Dict parcial para merge en fila (contrib_*, doc_nro, rubro_nombre, identity_mode).
    """
    mode = resolver_modo_identidad_operativa(ini, act_trabajo)
    origin = cargar_actuacion_origen(ini)

    if mode == COMPLETE_HISTORICAL and origin is not None:
        titular = resolve_titular_grid_fields(origin)
        dom = getattr(origin, "domicilio", None) or getattr(act_trabajo, "domicilio", None)
        out: Dict[str, Any] = {
            "identity_mode": COMPLETE_HISTORICAL,
            "contrib_apellido": titular.get("contrib_apellido"),
            "contrib_nombre": titular.get("contrib_nombre"),
            "razon_social": titular.get("razon_social"),
            "doc_nro": None,
            "rubro_nombre": None,
        }
        if dom is not None:
            out["calle"] = dom.calle
            out["numero"] = dom.numero
        return out

    authority = identidad_autoridad_desde_origen(ini)
    return {
        "identity_mode": COMPLETE_EXISTING,
        "contrib_apellido": authority.get("contrib_apellido"),
        "contrib_nombre": authority.get("contrib_nombre"),
        "razon_social": authority.get("razon_social"),
        "doc_nro": authority.get("doc_nro"),
        "rubro_nombre": authority.get("rubro_nombre"),
        "calle": authority.get("calle"),
        "numero": authority.get("numero"),
    }
