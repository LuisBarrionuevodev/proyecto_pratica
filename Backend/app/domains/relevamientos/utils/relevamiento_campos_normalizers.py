"""
Normalización de campos opcionales de establecimiento en relevamiento (PR7.3).
"""
from __future__ import annotations

import re

_SPACE_RE = re.compile(r"\s+")

ANGULOS_ESQUINA_VALIDOS = frozenset({"NE", "NO", "SE", "SO"})

NOMBRE_FANTASIA_MAX_LEN = 255


def normalizar_nombre_fantasia(value: str | None) -> str | None:
    """
    Normaliza nombre de fantasía: strip, colapsa espacios, trunca a 255, NULL si vacío.

    Parámetros:
        value: texto crudo o None.

    Retorno:
        Cadena normalizada o None.
    """
    if value is None:
        return None
    s = _SPACE_RE.sub(" ", str(value).strip())
    if not s:
        return None
    return s[:NOMBRE_FANTASIA_MAX_LEN]


def normalizar_angulo_esquina(value: str | None) -> str | None:
    """
    Normaliza ángulo de esquina: strip, upper, solo NE/NO/SE/SO.

    Parámetros:
        value: código de ángulo o None/vacío.

    Retorno:
        NE, NO, SE, SO o None si vacío.

    Errores:
        ValueError: si el valor no es vacío ni un ángulo válido.
    """
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if s not in ANGULOS_ESQUINA_VALIDOS:
        raise ValueError("Ángulo de esquina inválido. Use NE, NO, SE o SO.")
    return s


def resolver_angulo_esquina_para_persistencia(
    value: str | None,
    *,
    numero_tipo: str | None,
) -> str | None:
    """
    Resuelve ángulo para guardar en relevamiento.

    PR7.3: si el domicilio no es ESQUINA, no persistir ángulo (NULL) aunque venga en payload.
    Evita datos huérfanos sin romper requests legacy.

    Parámetros:
        value: ángulo crudo.
        numero_tipo: tipo del domicilio ya normalizado.

    Retorno:
        Ángulo canónico o None.

    Errores:
        ValueError: ángulo inválido cuando se envía valor no vacío.
    """
    angulo = normalizar_angulo_esquina(value)
    if angulo is None:
        return None
    if (numero_tipo or "").upper() != "ESQUINA":
        return None
    return angulo


def campos_establecimiento_desde_payload(
    payload: dict,
    *,
    numero_tipo: str | None,
) -> tuple[str | None, str | None]:
    """
    Extrae y normaliza nombre_fantasia y angulo_esquina desde payload canónico.

    Parámetros:
        payload: dict de create/update.
        numero_tipo: tipo de domicilio tras normalización.

    Retorno:
        Tupla (nombre_fantasia, angulo_esquina) listos para persistir.
    """
    nombre = normalizar_nombre_fantasia(payload.get("nombre_fantasia"))
    angulo = resolver_angulo_esquina_para_persistencia(
        payload.get("angulo_esquina"),
        numero_tipo=numero_tipo,
    )
    return nombre, angulo
