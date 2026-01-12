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
