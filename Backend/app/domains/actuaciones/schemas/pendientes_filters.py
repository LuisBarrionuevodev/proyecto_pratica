from __future__ import annotations

from datetime import date
from typing import Optional, Any

from pydantic import BaseModel, field_validator, model_validator


def _current_month_range() -> tuple[date, date]:
    """
    Retorna el rango (primer_día, último_día) del mes corriente.
    """
    today = date.today()
    first_day = date(today.year, today.month, 1)
    if today.month == 12:
        last_day = date(today.year, 12, 31)
    else:
        next_month = date(today.year, today.month + 1, 1)
        last_day = date(next_month.year, next_month.month, next_month.day - 1)
    return first_day, last_day


class ActuacionesPendientesFilters(BaseModel):
    """
    Schema para validar filtros de pendientes de Actuaciones.

    Filtros:
        - desde: fecha desde (YYYY-MM-DD)
        - hasta: fecha hasta (YYYY-MM-DD)
        - tipo: domicilios | sin_expediente | notificaciones
    """

    desde: Optional[date] = None
    hasta: Optional[date] = None
    tipo: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        value = str(v).strip().lower()
        if value not in {"domicilios", "sin_expediente", "notificaciones"}:
            raise ValueError("tipo inválido.")
        return value

    @model_validator(mode="after")
    def apply_defaults_and_validate_range(self) -> "ActuacionesPendientesFilters":
        """
        Defaults:
        - Si ambos son None → mes actual
        - Si solo `desde` → hasta = hoy
        - Si solo `hasta` → desde = primer día del mes de `hasta`
        """
        if self.desde is None and self.hasta is None:
            self.desde, self.hasta = _current_month_range()
        elif self.desde is not None and self.hasta is None:
            self.hasta = date.today()
        elif self.desde is None and self.hasta is not None:
            self.desde = date(self.hasta.year, self.hasta.month, 1)

        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")
        return self
