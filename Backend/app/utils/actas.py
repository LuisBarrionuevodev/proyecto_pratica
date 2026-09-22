from __future__ import annotations

from typing import Any, Optional


def acta_6(valor: Any) -> Optional[str]:
    """
    Normaliza numeros de acta/OT a 6 dígitos si son numéricos.
    Si viene vacío o None, devuelve None.
    """
    if valor is None:
        return None

    s = str(valor).strip()
    if not s:
        return None

    return s.zfill(6) if s.isdigit() else s


def format_ot_display(sequence_value: int) -> str:
    """
    Formatea un valor entero de secuencia OT con zero-padding mínimo de 6 dígitos.

    Parámetros:
        sequence_value: entero de secuencia global (>= 0).

    Retorno:
        Representación textual para ``numero_acta`` (sin truncar por encima de 6).
    """
    if sequence_value < 0:
        raise ValueError("sequence_value debe ser >= 0")
    return str(sequence_value).zfill(6)
