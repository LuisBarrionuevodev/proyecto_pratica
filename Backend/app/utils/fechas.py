from __future__ import annotations

from datetime import datetime
from typing import Any, Tuple


def parse_fecha_grid(fecha_str: Any) -> Tuple[int, int, datetime.date]:
    """
    Acepta:
      - "DD/MM/YYYY"
      - "YYYY-MM-DD"
    Devuelve: (mes, anio, date)
    """
    if fecha_str is None:
        raise ValueError("La fecha es obligatoria")

    s = str(fecha_str).strip()
    if not s:
        raise ValueError("La fecha es obligatoria")

    try:
        if "/" in s:
            dt = datetime.strptime(s, "%d/%m/%Y").date()
        else:
            dt = datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("Formato de fecha inválido. Usá DD/MM/YYYY o YYYY-MM-DD")

    return dt.month, dt.year, dt
