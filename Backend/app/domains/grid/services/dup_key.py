from __future__ import annotations

from typing import Any

from app.domains.actuaciones.schemas.grid.actuacion_row_in import ActuacionGridRowIn


def _normalize_ot(numero_ot: Any) -> str:
    s = ("" if numero_ot is None else str(numero_ot)).strip()
    return s.zfill(6) if s.isdigit() else s


def build_dup_key(row_validada: ActuacionGridRowIn) -> tuple[str, str]:
    """
    Regla de duplicado dentro del lote de actuaciones:
      orden_trabajo_numero + fecha_actuacion (ISO)
    """
    ot = _normalize_ot(row_validada.orden_trabajo_numero)
    fecha_iso = row_validada.fecha_as_date().isoformat()
    return (ot, fecha_iso)
