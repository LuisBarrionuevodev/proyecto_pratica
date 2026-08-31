"""
Clasificación canónica de circuito operativo (GESTIÓN-FIX.9).

Una sola semántica para validación, capabilities y políticas de identidad.
"""

from __future__ import annotations

from typing import Any

CIRCUITO_NORMAL = "NORMAL"
CIRCUITO_RELEVAMIENTO = "RELEVAMIENTO"
CIRCUITO_DENUNCIA = "DENUNCIA"
CIRCUITO_REINSPECCION_NOTIFICACION = "REINSPECCION_NOTIFICACION"
CIRCUITO_REINSPECCION_OFICIO = "REINSPECCION_OFICIO"

_CIRCUITOS_VALIDOS = frozenset(
    {
        CIRCUITO_NORMAL,
        CIRCUITO_RELEVAMIENTO,
        CIRCUITO_DENUNCIA,
        CIRCUITO_REINSPECCION_NOTIFICACION,
        CIRCUITO_REINSPECCION_OFICIO,
    }
)

_TIPOS_INICIADOR_OFICIO = frozenset(
    {
        "REINSPECCION_OFICIO",
        "RATIFICACION_CLAUSURA_OFICIO",
        "RATIFICACION_DECOMISO_OFICIO",
        "VERIFICAR_INFORMAR_OFICIO",
    }
)

_MAPA_CIRCUITO_DOCUMENTAL = {
    "REINSPECCION_NOTIFICACION": CIRCUITO_REINSPECCION_NOTIFICACION,
    "REINSPECCION_OFICIO": CIRCUITO_REINSPECCION_OFICIO,
    "COMUN_NOTIFICACION": CIRCUITO_NORMAL,
    "COMUN_COMPROBACION": CIRCUITO_NORMAL,
    "DESCONOCIDO": CIRCUITO_NORMAL,
}


def circuito_desde_tipo_iniciador(tipo_iniciador: str | None) -> str:
    """
    Resuelve circuito operativo desde ``IniciadorRuta.tipo_iniciador``.

    Parámetros:
        tipo_iniciador: valor persistido del iniciador.

    Retorno:
        Clave de circuito canónica.
    """
    if not tipo_iniciador:
        return CIRCUITO_NORMAL
    tipo = str(tipo_iniciador).strip().upper()
    if tipo == "RELEVAMIENTO":
        return CIRCUITO_RELEVAMIENTO
    if tipo == "DENUNCIA":
        return CIRCUITO_DENUNCIA
    if tipo == "REINSPECCION_NOTIFICACION":
        return CIRCUITO_REINSPECCION_NOTIFICACION
    if tipo in _TIPOS_INICIADOR_OFICIO:
        return CIRCUITO_REINSPECCION_OFICIO
    return CIRCUITO_NORMAL


def circuito_desde_documentacion_contexto(circuito_documental: str | None) -> str | None:
    """
    Mapea ``documentacion_contexto.circuito`` a circuito operativo si aplica.

    Parámetros:
        circuito_documental: valor del presenter F2.2.

    Retorno:
        Circuito canónico o None si no es concluyente.
    """
    if not circuito_documental:
        return None
    key = str(circuito_documental).strip().upper()
    mapped = _MAPA_CIRCUITO_DOCUMENTAL.get(key)
    if mapped in (CIRCUITO_REINSPECCION_NOTIFICACION, CIRCUITO_REINSPECCION_OFICIO):
        return mapped
    return None


def circuito_desde_actuacion_id(actuacion_id: int) -> str:
    """
    Resuelve circuito operativo de una actuación persistida (prioridad: iniciador).

    Parámetros:
        actuacion_id: PK de la actuación.

    Retorno:
        Circuito canónico.
    """
    from app.domains.actuaciones.services.actuacion_domicilio_edit_service import (
        resolve_iniciador_operativo_actuacion,
    )

    ini = resolve_iniciador_operativo_actuacion(int(actuacion_id))
    if ini is not None:
        return circuito_desde_tipo_iniciador(ini.tipo_iniciador)
    return CIRCUITO_NORMAL


def circuito_desde_row_dict(row: dict[str, Any]) -> str:
    """
    Resuelve circuito desde fila de grilla/API (sin DB).

    Prioridad: ``documentacion_contexto.circuito`` → flags de origen RN/Oficio.
    """
    doc = row.get("documentacion_contexto") or {}
    if isinstance(doc, dict):
        mapped = circuito_desde_documentacion_contexto(doc.get("circuito"))
        if mapped is not None:
            return mapped
    if row.get("origen_reinspeccion_notificacion"):
        return CIRCUITO_REINSPECCION_NOTIFICACION
    if row.get("origen_reinspeccion_oficio"):
        return CIRCUITO_REINSPECCION_OFICIO
    return CIRCUITO_NORMAL


def omite_identidad_operativa(circuito: str) -> bool:
    """
    True cuando el PUT/validación no debe exigir ni persistir identidad del establecimiento.

    Parámetros:
        circuito: circuito canónico.

    Retorno:
        True para reinspección por notificación u oficio.
    """
    return circuito in (CIRCUITO_REINSPECCION_NOTIFICACION, CIRCUITO_REINSPECCION_OFICIO)


def build_actuacion_grid_validation_context(actuacion_id: int) -> dict[str, Any]:
    """
    Contexto Pydantic unificado para ``ActuacionGridRowIn`` y validate_service.

    Parámetros:
        actuacion_id: PK de la actuación en edición.

    Retorno:
        Dict con ``circuito_operativo``, ``omite_identidad_operativa`` y compat FIX.6.
    """
    circuito = circuito_desde_actuacion_id(int(actuacion_id))
    omite = omite_identidad_operativa(circuito)
    return {
        "circuito_operativo": circuito,
        "omite_identidad_operativa": omite,
        "es_reinspeccion_oficio": circuito == CIRCUITO_REINSPECCION_OFICIO,
    }


def normalizar_circuito(value: str | None) -> str:
    """Valida y normaliza una clave de circuito; fallback NORMAL."""
    if not value:
        return CIRCUITO_NORMAL
    key = str(value).strip().upper()
    if key in _CIRCUITOS_VALIDOS:
        return key
    return CIRCUITO_NORMAL
