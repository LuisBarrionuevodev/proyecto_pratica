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
    STORED_NO_PERMITE_INSPECCION,
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

_DENUNCIA = _BASE_INSPECCION

_TIPO_A_SET: dict[str, frozenset[str]] = {
    "RELEVAMIENTO": _BASE_INSPECCION,
    "DENUNCIA": _DENUNCIA,
    "REINSPECCION_NOTIFICACION": _REINSPECCION,
    "REINSPECCION_OFICIO": _REINSPECCION,
}


def _keys_permitidos(tipo_iniciador: str | None) -> frozenset[str]:
    t = (tipo_iniciador or "").strip().upper()
    base = _TIPO_A_SET.get(t, _BASE_INSPECCION)
    return frozenset(_loose_key(x) for x in base)


def contraproducencia_permitida_en_completar_trabajo(
    tipo_iniciador: str | None,
    nombre: str | None,
) -> bool:
    """
    True si la contraproducencia (nombre de catálogo o valor persistido) aplica al tipo de iniciador.

    Parámetros:
        tipo_iniciador: p. ej. REINSPECCION_OFICIO.
        nombre: valor coercido de catálogo o persistido (LOCAL CERRADO, NO_EXISTE_LOCAL, …).

    Retorno:
        False para NO_HUBO y valores fuera del set del tipo.
    """
    if not nombre or not str(nombre).strip():
        return True
    if _loose_key(str(nombre)) == _loose_key("NO_HUBO"):
        return False
    return _loose_key(str(nombre)) in _keys_permitidos(tipo_iniciador)


def nombres_contraproducencia_completar_trabajo(tipo_iniciador: str | None) -> list[str]:
    """Lista ordenada de nombres de catálogo sugeridos para UI (Completar trabajo)."""
    t = (tipo_iniciador or "").strip().upper()
    base = _TIPO_A_SET.get(t, _BASE_INSPECCION)
    return sorted(base)
