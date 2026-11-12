"""
Proyección read-only de actas de origen (decomiso / kilos / clausura) desde la actuación ancla.

Regla: ``IniciadorRuta.actuacion_id`` → actuación origen → ``Decomiso`` / ``Clausura``.
Nunca leer decomiso, kilos o clausura de la actuación de visita / reinspección.
"""

from __future__ import annotations

import unicodedata
from decimal import Decimal
from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Clausura, Decomiso, IniciadorRuta, RutaItem

_TIPO_RAT_DECOMISO = "RATIFICACION DE DECOMISO"
_TIPO_RAT_CLAUSURA = "RATIFICACION DE CLAUSURA"
_TIPO_VERIFICAR_INFORMAR = "VERIFICAR E INFORMAR"

_TIPOS_VISITA_CATALOG = frozenset(
    {
        _TIPO_RAT_DECOMISO,
        _TIPO_RAT_CLAUSURA,
        _TIPO_VERIFICAR_INFORMAR,
    }
)

_TIPO_INICIADOR_A_FINAL = {
    "VERIFICAR_INFORMAR_OFICIO": _TIPO_VERIFICAR_INFORMAR,
    "RATIFICACION_CLAUSURA_OFICIO": _TIPO_RAT_CLAUSURA,
    "RATIFICACION_DECOMISO_OFICIO": _TIPO_RAT_DECOMISO,
}


def origen_actas_vacio() -> Dict[str, Any]:
    """
    Contrato estable de ``origen_actas`` sin ancla ni actas.

    Retorno:
        Dict con las cuatro claves en ``None``.
    """
    return {
        "actuacion_origen_id": None,
        "acta_decomiso_num": None,
        "decomiso_kilos_total": None,
        "acta_clausura_num": None,
    }


def _norm_tipo(s: str | None) -> str:
    if not s:
        return ""
    t = str(s).strip().upper().replace("_", " ")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def resolver_tipo_final_origen(
    *,
    tipo_actuacion_visita: str | None = None,
    tipo_iniciador: str | None = None,
) -> Optional[str]:
    """
    Tipo final de visita para enmascarar ``origen_actas`` (catálogo de actuación).

    Preferencia: ``actuaciones.tipo`` de la visita si es ratificación / verificar e informar;
    si no, mapeo del ``tipo_iniciador`` promovido. ``REINSPECCION`` genérico → ``None``
    (datos disponibles, sin afirmar ratificación).

    Parámetros:
        tipo_actuacion_visita: ``Actuaciones.tipo`` de la visita de cierre, si existe.
        tipo_iniciador: ``IniciadorRuta.tipo_iniciador``.

    Retorno:
        String de catálogo o ``None``.
    """
    raw = tipo_actuacion_visita
    if raw:
        n = _norm_tipo(raw)
        for catalogo in _TIPOS_VISITA_CATALOG:
            if n == _norm_tipo(catalogo):
                return catalogo
    mapped = _TIPO_INICIADOR_A_FINAL.get(str(tipo_iniciador or "").strip())
    if mapped:
        return mapped
    return None


def _kilos_float(cantidad: Any) -> Optional[float]:
    if cantidad is None:
        return None
    if isinstance(cantidad, Decimal):
        return float(cantidad)
    try:
        return float(cantidad)
    except (TypeError, ValueError):
        return None


def _aplicar_mascara_tipo_final(payload: Dict[str, Any], tipo_final: str | None) -> Dict[str, Any]:
    """
    Recorta campos de origen según el tipo final de la visita.

    Ratificación de decomiso: solo decomiso + kilos.
    Ratificación de clausura: solo clausura.
    Verificar e informar / pendiente / genérico: lo que exista, sin afirmar ratificación.
    """
    n = _norm_tipo(tipo_final)
    if n == _norm_tipo(_TIPO_RAT_DECOMISO):
        payload["acta_clausura_num"] = None
    elif n == _norm_tipo(_TIPO_RAT_CLAUSURA):
        payload["acta_decomiso_num"] = None
        payload["decomiso_kilos_total"] = None
    return payload


def origen_actas_desde_ancla(
    act_ancla: Actuaciones | None,
    *,
    tipo_final: str | None = None,
) -> Dict[str, Any]:
    """
    Lee decomiso/kilos/clausura de la actuación ancla (nunca de la visita).

    Parámetros:
        act_ancla: actuación origen (``IniciadorRuta.actuacion_id`` o fila Recorrido).
        tipo_final: tipo de visita para enmascarar campos; ``None`` = datos disponibles.

    Retorno:
        Dict ``origen_actas``. Campos ausentes en BD quedan ``None`` (sin inferencias).

    Errores:
        Ninguno (solo lectura).
    """
    if act_ancla is None or getattr(act_ancla, "id", None) is None:
        return origen_actas_vacio()

    ancla_id = int(act_ancla.id)
    decomiso = Decomiso.query.filter_by(actuacion_id=ancla_id).first()
    clausura = Clausura.query.filter_by(actuacion_id=ancla_id).first()
    payload: Dict[str, Any] = {
        "actuacion_origen_id": ancla_id,
        "acta_decomiso_num": getattr(decomiso, "numero_acta", None) if decomiso else None,
        "decomiso_kilos_total": _kilos_float(getattr(decomiso, "cantidad", None)) if decomiso else None,
        "acta_clausura_num": getattr(clausura, "numero_acta", None) if clausura else None,
    }
    return _aplicar_mascara_tipo_final(payload, tipo_final)


def origen_actas_desde_iniciador(
    ini: IniciadorRuta | None,
    *,
    tipo_final: str | None = None,
    tipo_actuacion_visita: str | None = None,
) -> Dict[str, Any]:
    """
    ``origen_actas`` desde ``IniciadorRuta.actuacion_id`` (ancla), no desde la visita.

    Parámetros:
        ini: iniciador de oficio/reinspección.
        tipo_final: override de tipo de visita; si falta se resuelve con visita + iniciador.
        tipo_actuacion_visita: ``Actuaciones.tipo`` de la visita (opcional).

    Retorno:
        Dict ``origen_actas`` vacío si no hay iniciador o no tiene ``actuacion_id``.

    Errores:
        Ninguno (solo lectura).
    """
    if ini is None or getattr(ini, "actuacion_id", None) is None:
        return origen_actas_vacio()
    resolved = tipo_final
    if resolved is None:
        resolved = resolver_tipo_final_origen(
            tipo_actuacion_visita=tipo_actuacion_visita,
            tipo_iniciador=getattr(ini, "tipo_iniciador", None),
        )
    act = db.session.get(Actuaciones, int(ini.actuacion_id))
    return origen_actas_desde_ancla(act, tipo_final=resolved)


def actuacion_ancla_origen(act: Actuaciones) -> Actuaciones:
    """
    Si ``act`` es visita de oficio, devuelve la ancla ``IniciadorRuta.actuacion_id``.

    Si no hay ítem de ruta / iniciador, o el iniciador apunta a la misma actuación,
    devuelve ``act`` (es la ancla o no hay circuito oficio).

    Parámetros:
        act: actuación consultada (ficha documental / Recorrido).

    Retorno:
        Actuación ancla de origen.

    Errores:
        Ninguno (solo lectura).
    """
    item = (
        RutaItem.query.filter(
            RutaItem.actuacion_id == int(act.id),
            RutaItem.deleted_at.is_(None),
        )
        .order_by(RutaItem.id.desc())
        .first()
    )
    if item is None or item.iniciador_ruta_id is None:
        return act
    ini = db.session.get(IniciadorRuta, int(item.iniciador_ruta_id))
    if ini is None or ini.actuacion_id is None:
        return act
    if int(ini.actuacion_id) == int(act.id):
        return act
    ancla = db.session.get(Actuaciones, int(ini.actuacion_id))
    return ancla if ancla is not None else act
