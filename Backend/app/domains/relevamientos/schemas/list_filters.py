from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class RelevamientosListFilters(BaseModel):
    """
    Schema para validar y normalizar filtros de listado de relevamientos.

    Filtros:
        - desde: fecha desde (YYYY-MM-DD)
        - hasta: fecha hasta (YYYY-MM-DD)
        - inspector: nombre o id (string)
        - calle: texto libre
        - numero: texto libre
        - page: página actual (default 1)
        - page_size: tamaño de página (default 50)
    """

    desde: Optional[date] = None
    hasta: Optional[date] = None
    inspector: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    page: int = 1
    page_size: int = 50

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page debe ser >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page_size debe ser >= 1")
        if v > 500:
            raise ValueError("page_size no puede superar 500")
        return v

    @model_validator(mode="after")
    def apply_defaults_and_validate_range(self) -> "RelevamientosListFilters":
        """
        Defaults:
        - Si solo `desde` → hasta = hoy
        - Si solo `hasta` → desde = primer día del mes de `hasta`
        - Si ambos son None → mes actual
        """
        if self.desde is None and self.hasta is None:
            today = date.today()
            self.desde = date(today.year, today.month, 1)
            if today.month == 12:
                self.hasta = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                self.hasta = date(next_month.year, next_month.month, next_month.day - 1)
        elif self.desde is not None and self.hasta is None:
            self.hasta = date.today()
        elif self.desde is None and self.hasta is not None:
            self.desde = date(self.hasta.year, self.hasta.month, 1)

        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")
        return self
