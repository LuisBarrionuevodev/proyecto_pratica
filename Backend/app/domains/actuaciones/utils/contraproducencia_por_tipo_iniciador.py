"""
Catálogo visible de contraproducencias según tipo de iniciador (STAB-4 / Completar trabajo).

Valores alineados al seed ``catalog_contraproducencia`` (run.py / migraciones).
NO_HUBO queda fuera de Completar trabajo; solo aplica en carga manual de actuación.
"""

from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    STORED_CORRECTIVA_DIRECCION_INCORRECTA,
    STORED_CORRECTIVA_NO_ES_EL_RUBRO,
    STORED_NO_EXISTE_LOCAL,
    STORED_NO_PAGO_DECOMISO,
    STORED_NO_PERMITE_INSPECCION,
    STORED_NO_SE_RATIFICO,
    _loose_key,
)

# Nombres de catálogo (persistidos tras normalize en cierre).
_BASE_INSPECCION = frozenset(
    {
        "LOCAL CERRADO",
        "CLIMA",
        "ZONA ROJA",
        "OTROS",
        STORED_CORRECTIVA_NO_ES_EL_RUBRO,
        STORED_CORRECTIVA_DIRECCION_INCORRECTA,
        STORED_NO_EXISTE_LOCAL,
        "NO EXISTE/NO ES EL RUBRO",
        STORED_NO_PERMITE_INSPECCION,
    }
)

_REINSPECCION = frozenset(
    {
        "LOCAL CERRADO",
        "CLIMA",
        "OTROS",
        STORED_NO_EXISTE_LOCAL,
        "NO EXISTE/NO ES EL RUBRO",
        STORED_NO_PERMITE_INSPECCION,
    }
)

_REINSPECCION_OFICIO = _REINSPECCION | frozenset(
    {
        STORED_NO_SE_RATIFICO,
        STORED_NO_PAGO_DECOMISO,
    }
)

_DENUNCIA = _BASE_INSPECCION

_TIPO_A_SET: dict[str, frozenset[str]] = {
    "RELEVAMIENTO": _BASE_INSPECCION,
    "DENUNCIA": _DENUNCIA,
    "REINSPECCION_NOTIFICACION": _REINSPECCION,
    "REINSPECCION_OFICIO": _REINSPECCION_OFICIO,
}

_TIPO_ACTUACION_RATIFICACION_CLAUSURA = "RATIFICACION DE CLAUSURA"
_TIPO_ACTUACION_RATIFICACION_DECOMISO = "RATIFICACION DE DECOMISO"


def _normalizar_tipo_actuacion_oficio(tipo_actuacion: str | None) -> str:
    return _loose_key((tipo_actuacion or "").strip())


def _contraproducencia_oficio_coherente_con_tipo_actuacion(
    nombre: str,
    tipo_actuacion: str | None,
) -> bool:
    """Filtra contras de oficio según subtipo (ratificación clausura / decomiso)."""
    key = _loose_key(nombre)
    tipo = _normalizar_tipo_actuacion_oficio(tipo_actuacion)
    if key == _loose_key(STORED_NO_SE_RATIFICO):
        return tipo == _loose_key(_TIPO_ACTUACION_RATIFICACION_CLAUSURA)
    if key == _loose_key(STORED_NO_PAGO_DECOMISO):
        return tipo == _loose_key(_TIPO_ACTUACION_RATIFICACION_DECOMISO)
    return True


def _keys_permitidos(tipo_iniciador: str | None) -> frozenset[str]:
    t = (tipo_iniciador or "").strip().upper()
    base = _TIPO_A_SET.get(t, _BASE_INSPECCION)
    return frozenset(_loose_key(x) for x in base)


def contraproducencia_permitida_en_completar_trabajo(
    tipo_iniciador: str | None,
    nombre: str | None,
    *,
    tipo_actuacion: str | None = None,
) -> bool:
    """
    True si la contraproducencia (nombre de catálogo o valor persistido) aplica al tipo de iniciador.

    Parámetros:
        tipo_iniciador: p. ej. REINSPECCION_OFICIO.
        nombre: valor coercido de catálogo o persistido (LOCAL CERRADO, NO_EXISTE_LOCAL, …).
        tipo_actuacion: subtipo de actuación en REINSPECCION_OFICIO (ratificación / verificar).

    Retorno:
        False para NO_HUBO y valores fuera del set del tipo.
    """
    if not nombre or not str(nombre).strip():
        return True
    if _loose_key(str(nombre)) == _loose_key("NO_HUBO"):
        return False
    if _loose_key(str(nombre)) not in _keys_permitidos(tipo_iniciador):
        return False
    t = (tipo_iniciador or "").strip().upper()
    if t == "REINSPECCION_OFICIO":
        return _contraproducencia_oficio_coherente_con_tipo_actuacion(str(nombre), tipo_actuacion)
    return True


def nombres_contraproducencia_completar_trabajo(tipo_iniciador: str | None) -> list[str]:
    """Lista ordenada de nombres de catálogo sugeridos para UI (Completar trabajo)."""
    t = (tipo_iniciador or "").strip().upper()
    base = _TIPO_A_SET.get(t, _BASE_INSPECCION)
    return sorted(base)
