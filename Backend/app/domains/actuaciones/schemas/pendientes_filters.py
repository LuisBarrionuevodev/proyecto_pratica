from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Any

from pydantic import BaseModel, field_validator, model_validator


def _coerce_bool_optional(v: Any) -> bool:
    if v is None or v == "":
        return False
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return False


def _current_month_range() -> tuple[date, date]:
    """
    Retorna el rango (primer_día, último_día) del mes corriente.
    """
    today = date.today()
    first_day = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)
    last_day = next_month_first - timedelta(days=1)
    return first_day, last_day


class ActuacionesPendientesFilters(BaseModel):
    """
    Schema para validar filtros de pendientes de Actuaciones.

    Filtros:
        - desde: fecha desde (YYYY-MM-DD)
        - hasta: fecha hasta (YYYY-MM-DD)
        - tipo: domicilios | sin_expediente | notificaciones
        - source_type: all | notificacion | comprobacion (solo para pendientes de expediente)
    """

    desde: Optional[date] = None
    hasta: Optional[date] = None
    tipo: Optional[str] = None
    source_type: Optional[str] = None
    # Filtro opcional por domicilio.distrito_id (bandejas comprobación / recorrido).
    distrito_id: Optional[int] = None
    # Si vienen ambos, fijan el rango de fechas al mes completo (recorrido / consultas).
    mes: Optional[int] = None
    anio: Optional[int] = None
    # Si es True: no aplicar rango por defecto (mes actual) cuando desde/hasta vienen vacíos.
    # Uso previsto: bandeja «Pendientes de expediente» rama COMPROBACION (todo el histórico pendiente).
    omitir_rango_fecha: bool = False
    # Filtros documentales opcionales (solo aplican en service con ``source_type=notificacion``).
    contribuyente_q: Optional[str] = None
    calle_q: Optional[str] = None
    numero_notificacion: Optional[str] = None
    numero_comprobacion: Optional[str] = None
    motivo_q: Optional[str] = None
    # Historial notificación: filtro exacto por FK motivo (selector en UI).
    motivo_id: Optional[int] = None
    # Filtros operativos (En plazo / Por vencer): aplican tras ``plazo_slice`` en service.
    orden_trabajo: Optional[str] = None
    # Solo aplica con ``source_type=notificacion`` en pendientes/expediente.
    plazo_slice: Optional[str] = None
    # Paginación server-side (Historial notificaciones); no enviar en bandeja operativa.
    page: Optional[int] = None
    page_size: Optional[int] = None

    @field_validator("omitir_rango_fecha", mode="before")
    @classmethod
    def _omitir_rango_fecha_bool(cls, v: Any) -> bool:
        return _coerce_bool_optional(v)

    @field_validator("distrito_id", "mes", "anio", "page", "page_size", "motivo_id", mode="before")
    @classmethod
    def _empty_int_optional(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    @field_validator(
        "contribuyente_q",
        "calle_q",
        "numero_notificacion",
        "numero_comprobacion",
        "motivo_q",
        "orden_trabajo",
        mode="before",
    )
    @classmethod
    def _strip_optional_q(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        value = str(v).strip().lower()
        if value not in {"domicilios", "sin_expediente", "notificaciones"}:
            raise ValueError("tipo inválido.")
        return value

    @field_validator("plazo_slice")
    @classmethod
    def validate_plazo_slice(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        value = str(v).strip().lower()
        if value not in {"en_plazo", "por_vencer", "total"}:
            raise ValueError("plazo_slice inválido.")
        return value

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: Optional[str]) -> Optional[str]:
        """
        Normaliza source_type para filtros de pendientes de expediente.
        """
        if v is None or v == "":
            return "all"
        value = str(v).strip().lower()
        if value not in {"all", "notificacion", "comprobacion"}:
            raise ValueError("source_type inválido.")
        return value

    @model_validator(mode="after")
    def apply_defaults_and_validate_range(self) -> "ActuacionesPendientesFilters":
        """
        Defaults:
        - Si `mes` y `anio` están definidos → rango = ese mes calendario completo
        - Si ambos desde/hasta son None → mes actual (salvo ``omitir_rango_fecha=True``)
        - Si solo `desde` → hasta = hoy
        - Si solo `hasta` → desde = primer día del mes de `hasta`
        """
        if self.mes is not None and self.anio is not None:
            if not 1 <= int(self.mes) <= 12:
                raise ValueError("mes debe estar entre 1 y 12")
            y, m = int(self.anio), int(self.mes)
            first = date(y, m, 1)
            last = date(y, m, monthrange(y, m)[1])
            self.desde = first
            self.hasta = last
        elif self.desde is None and self.hasta is None:
            if not self.omitir_rango_fecha:
                self.desde, self.hasta = _current_month_range()
        elif self.desde is not None and self.hasta is None:
            self.hasta = date.today()
        elif self.desde is None and self.hasta is not None:
            self.desde = date(self.hasta.year, self.hasta.month, 1)

        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("desde debe ser menor o igual que hasta")
        if self.page is not None and int(self.page) < 1:
            raise ValueError("page debe ser >= 1")
        if self.page_size is not None and int(self.page_size) < 1:
            raise ValueError("page_size debe ser >= 1")
        return self
