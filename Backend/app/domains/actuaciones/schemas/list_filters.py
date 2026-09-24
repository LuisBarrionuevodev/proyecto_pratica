from __future__ import annotations

from datetime import date
from typing import Optional, Any

from sqlalchemy import func
from pydantic import BaseModel, field_validator, model_validator

from app.database import db
from app.models import CatalogTipoActuacion, CatalogContraproducencia
from app.utils.actas import acta_6


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

    if today.month == 12:
        last_day = date(today.year, 12, 31)
    else:
        next_month = date(today.year, today.month + 1, 1)
        last_day = date(next_month.year, next_month.month, next_month.day - 1)

    return first_day, last_day


def _has_anchor_filters(
    *,
    q: Optional[str],
    orden_trabajo: Optional[str],
    actuacion_id: Optional[int],
    calle_q: Optional[str],
    documento_q: Optional[str],
    contribuyente_q: Optional[str],
    inspector_id: Optional[int],
    acta_inspeccion: Optional[str],
    acta_notificacion: Optional[str],
    acta_comprobacion: Optional[str],
    acta_clausura: Optional[str],
    acta_decomiso: Optional[str],
) -> bool:
    """Filtros que no deben forzar defaults de rango de fechas (STAB-6 / PERF.1-A2)."""
    return bool(
        q
        or orden_trabajo
        or actuacion_id
        or calle_q
        or documento_q
        or contribuyente_q
        or inspector_id
        or acta_inspeccion
        or acta_notificacion
        or acta_comprobacion
        or acta_clausura
        or acta_decomiso
    )


class ActuacionesListFilters(BaseModel):
    """
    Schema para validar y normalizar filtros de listado de actuaciones.

    Filtros:
        - desde / hasta: rango de fechas
        - tipo / contraproducencia: catálogos
        - orden_trabajo: OT exacta (acta_6)
        - calle_q, documento_q, contribuyente_q, inspector_id: filtros específicos (PERF.1-A2)
        - acta_*: número de acta por tipo
        - q: legacy compatibility (búsqueda global OR + joins)
        - page / page_size: paginación servidor
    """
    desde: Optional[date] = None
    hasta: Optional[date] = None
    tipo: Optional[str] = None
    contraproducencia: Optional[str] = None
    orden_trabajo: Optional[str] = None
    actuacion_id: Optional[int] = None
    q: Optional[str] = None
    calle_q: Optional[str] = None
    documento_q: Optional[str] = None
    contribuyente_q: Optional[str] = None
    inspector_id: Optional[int] = None
    acta_inspeccion: Optional[str] = None
    acta_notificacion: Optional[str] = None
    acta_comprobacion: Optional[str] = None
    acta_clausura: Optional[str] = None
    acta_decomiso: Optional[str] = None
    page: int = 1
    page_size: int = 50

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
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

    @field_validator("inspector_id")
    @classmethod
    def validate_inspector_id(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if int(v) < 1:
            raise ValueError("inspector_id debe ser >= 1")
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

    @field_validator("calle_q", "contribuyente_q")
    @classmethod
    def validate_text_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip()
        if len(s) < 2:
            raise ValueError("El filtro de texto debe tener al menos 2 caracteres")
        return s

    @field_validator("documento_q")
    @classmethod
    def validate_documento_q(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip().replace(" ", "").replace("-", "")
        if len(s) < 2:
            raise ValueError("documento_q debe tener al menos 2 caracteres")
        return s

    @field_validator(
        "acta_inspeccion",
        "acta_notificacion",
        "acta_comprobacion",
        "acta_clausura",
        "acta_decomiso",
    )
    @classmethod
    def validate_acta_num(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        s = str(v).strip()
        if not s:
            return None
        return acta_6(s) or s

    @field_validator("orden_trabajo")
    @classmethod
    def validate_orden_trabajo(cls, v: Optional[str]) -> Optional[str]:
        s = _clean_str(v)
        return s

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
    def apply_defaults_and_validate_range(self) -> "ActuacionesListFilters":
        busqueda_global = _has_anchor_filters(
            q=self.q,
            orden_trabajo=self.orden_trabajo,
            actuacion_id=self.actuacion_id,
            calle_q=self.calle_q,
            documento_q=self.documento_q,
            contribuyente_q=self.contribuyente_q,
            inspector_id=self.inspector_id,
            acta_inspeccion=self.acta_inspeccion,
            acta_notificacion=self.acta_notificacion,
            acta_comprobacion=self.acta_comprobacion,
            acta_clausura=self.acta_clausura,
            acta_decomiso=self.acta_decomiso,
        )

        if not busqueda_global:
            if self.desde is not None and self.hasta is None:
                self.hasta = date.today()
            elif self.desde is None and self.hasta is not None:
                self.desde = date(self.hasta.year, self.hasta.month, 1)

        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")

        return self
