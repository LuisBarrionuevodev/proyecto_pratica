from __future__ import annotations

from datetime import date
from typing import Optional, Any

from sqlalchemy import func
from pydantic import BaseModel, field_validator, model_validator

from app.database import db
from app.models import CatalogTipoActuacion, CatalogContraproducencia


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _upper_norm(s: str) -> str:
    s = s.strip().upper().replace("_", " ")
    return " ".join(s.split())


def _normalize_catalog_input(value: Any, strip_prefix: Optional[str] = None) -> Optional[str]:
    s = _clean_str(value)
    if not s:
        return None
    s = _upper_norm(s)
    if strip_prefix and s.startswith(strip_prefix):
        s = s.split(".", 1)[1].strip()
    return s


def _coerce_catalog_value(
    value: Any,
    model_cls: type[db.Model],
    field_label: str,
    strip_prefix: Optional[str] = None,
) -> Optional[str]:
    normalized = _normalize_catalog_input(value, strip_prefix=strip_prefix)
    if not normalized:
        return None
    row = (
        db.session.query(model_cls.nombre)
        .filter(func.replace(func.upper(model_cls.nombre), "_", " ") == normalized)
        .limit(1)
        .first()
    )
    if row is None:
        raise ValueError(f"{field_label} debe ser un valor válido del catálogo.")
    return row[0]


def get_current_month_range() -> tuple[date, date]:
    """
    Retorna el rango (primer_día, último_día) del mes corriente.
    
    Returns:
        (primer_día_del_mes, último_día_del_mes)
    """
    today = date.today()
    first_day = date(today.year, today.month, 1)
    
    # Último día del mes: día anterior al primer día del mes siguiente
    if today.month == 12:
        last_day = date(today.year, 12, 31)
    else:
        next_month = date(today.year, today.month + 1, 1)
        last_day = date(next_month.year, next_month.month, next_month.day - 1)
    
    return first_day, last_day


class ActuacionesListFilters(BaseModel):
    """
    Schema para validar y normalizar filtros de listado de actuaciones.
    
    Filtros:
        - desde: fecha desde (YYYY-MM-DD)
        - hasta: fecha hasta (YYYY-MM-DD)
        - tipo: enum tipo de actuación (INSPECCION, REINSPECCION, etc.)
        - contraproducencia: enum contraproducencia (LOCAL CERRADO, etc.)
        - orden_trabajo: número de orden de trabajo (búsqueda exacta)
        - page: página actual (default 1)
        - page_size: tamaño de página (default 50)
    
    Defaults:
        - Si solo `desde` → hasta = hoy
        - Si solo `hasta` → desde = primer día del mes de `hasta`
        - Los filtros son INDEPENDIENTES: se puede buscar por cualquier combinación
    
    Validaciones:
        - desde <= hasta (si ambos están presentes)
    """
    desde: Optional[date] = None
    hasta: Optional[date] = None
    tipo: Optional[str] = None
    contraproducencia: Optional[str] = None
    orden_trabajo: Optional[str] = None
    actuacion_id: Optional[int] = None
    q: Optional[str] = None
    page: int = 1
    page_size: int = 50

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
        """Valida que tipo sea un valor válido del enum."""
        if v is None or v == "":
            return None
        
        return _coerce_catalog_value(
            v,
            CatalogTipoActuacion,
            "tipo",
            strip_prefix="TIPO.",
        )

    @field_validator("contraproducencia")
    @classmethod
    def validate_contraproducencia(cls, v: Optional[str]) -> Optional[str]:
        """Valida que contraproducencia sea un valor válido del enum."""
        if v is None or v == "":
            return None
        
        return _coerce_catalog_value(
            v,
            CatalogContraproducencia,
            "contraproducencia",
        )

    @field_validator("actuacion_id")
    @classmethod
    def validate_actuacion_id(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if int(v) < 1:
            raise ValueError("actuacion_id debe ser >= 1")
        return int(v)

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip()
        if len(s) < 2:
            raise ValueError("q debe tener al menos 2 caracteres")
        return s

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        """Valida que page sea >= 1."""
        if v < 1:
            raise ValueError("page debe ser >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Valida que page_size esté entre 1 y 500."""
        if v < 1:
            raise ValueError("page_size debe ser >= 1")
        if v > 500:
            raise ValueError("page_size no puede superar 500")
        return v

    @model_validator(mode="after")
    def apply_defaults_and_validate_range(self) -> "ActuacionesListFilters":
        """
        Aplica defaults según la lógica solicitada:
        
        1. Si `desde` y `hasta` son None Y hay otros filtros → NO aplicar defaults (búsqueda independiente)
        2. Si solo `desde` → hasta = hoy
        3. Si solo `hasta` → desde = primer día del mes de `hasta`
        4. Valida que desde <= hasta
        
        Los filtros son independientes: se puede buscar solo por tipo, contraproducencia u orden_trabajo
        sin necesidad de especificar fechas.
        """
        busqueda_global = bool(self.q or self.orden_trabajo or self.actuacion_id)

        # STAB-6: búsqueda por OT / id / texto no fuerza rango de fechas
        if not busqueda_global:
            if self.desde is not None and self.hasta is None:
                self.hasta = date.today()
            elif self.desde is None and self.hasta is not None:
                self.desde = date(self.hasta.year, self.hasta.month, 1)
        
        # Validar que desde <= hasta (solo si ambos están presentes)
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")
        
        return self
