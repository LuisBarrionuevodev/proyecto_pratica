from __future__ import annotations

import re
from datetime import datetime, date
from typing import Any, Optional, Dict, Type

from sqlalchemy import func
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.database import db
from app.models import (
    CatalogTipoActuacion,
    CatalogContraproducencia,
    CatalogMotivoComprobacion,
)

# ===== En
# ===== Helpers de normalización =====
_SPACE_RE = re.compile(r"\s+")


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _upper_norm(s: str) -> str:
    # normaliza espacios y uppercase
    s = s.strip().upper()
    s = s.replace("_", " ")
    s = _SPACE_RE.sub(" ", s)
    return s


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
    model_cls: Type[db.Model],
    field_label: str,
    strip_prefix: Optional[str] = None,
) -> Optional[str]:
    """
    Normaliza y valida contra catálogo DB. Devuelve el nombre canónico de la DB.
    """
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
        raise ValueError(f"{field_label} inválido.")
    return row[0]


def _matches_catalog(value: Optional[str], expected: str) -> bool:
    if not value:
        return False
    return _upper_norm(value) == _upper_norm(expected)


def _parse_fecha(v: Any) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    s = _clean_str(v)
    if not s:
        raise ValueError("Fecha requerida.")
    # YYYY-MM-DD
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    # DD/MM/YYYY
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError as e:
        raise ValueError("Formato de fecha inválido. Use DD/MM/YYYY o YYYY-MM-DD.") from e


def _zfill6_if_digit(v: Any) -> Optional[str]:
    s = _clean_str(v)
    if not s:
        return None
    # Regla: actas/OT deben ser solo números (no letras)
    if not s.isdigit():
        raise ValueError("Debe ser numérico.")
    return s.zfill(6)


def _only_digits(v: Any) -> Optional[str]:
    """Valida que el valor contenga solo dígitos (si viene vacío, retorna None)."""
    s = _clean_str(v)
    if not s:
        return None
    if not s.isdigit():
        raise ValueError("Debe ser numérico.")
    return s


def _raise_field_errors(model_name: str, field_errors: Dict[str, str]) -> None:
    """
    Genera errores por campo (celda-friendly) usando ValidationError.from_exception_data.
    Compatible con Pydantic v2 (requiere ctx para value_error).
    """
    errs = []
    for field, msg in field_errors.items():
        errs.append(
            {
                "type": "value_error",
                "loc": (field,),
                "msg": "Value error",
                "input": None,
                "ctx": {"error": msg},
            }
        )
    raise ValidationError.from_exception_data(model_name, errs)


class ActuacionGridRowIn(BaseModel):
    """
    Fila proveniente de la grilla (Glide/React Table).
    Enfoque:
    - Normalizar strings
    - Parsear fecha a date
    - Validar catálogos en DB
    - Validar reglas de negocio base con errores por CELDA
    """

    id: Optional[int] = Field(default=None, ge=1)

    @field_validator("id", mode="before")
    @classmethod
    def parse_id(cls, v: Any):
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if s.isdigit():
            return int(s)
        raise ValueError("id inválido")

    # OT y fecha
    orden_trabajo_numero: str = Field(..., min_length=1)
    fecha_actuacion: date

    # Catálogos / clasificación
    rubro_nombre: Optional[str] = None
    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None

    # Inspectores (catálogo DB)
    inspector1: Optional[str] = None
    inspector2: Optional[str] = None
    inspector3: Optional[str] = None

    # Domicilio
    calle: Optional[str] = None
    numero: Optional[str] = None  # permite str libre (ej: esquina, s/n)

    # Contribuyente
    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None

    # Actas
    acta_inspeccion_num: Optional[str] = None

    acta_notificacion_num: Optional[str] = None
    notificacion_motivo_1: Optional[str] = None
    notificacion_motivo_2: Optional[str] = None
    notificacion_motivo_3: Optional[str] = None

    acta_comprobacion_num: Optional[str] = None
    comprobacion_motivo: Optional[str] = None

    acta_clausura_num: Optional[str] = None

    acta_decomiso_num: Optional[str] = None
    decomiso_kilos_total: Optional[float] = None

    # Expediente / Oficio
    expediente_numero: Optional[str] = None
    expediente_anio: Optional[int] = None

    oficio_numero: Optional[str] = None
    oficio_anio: Optional[int] = None
    oficio_causa: Optional[str] = None

    # Previas
    notificacion_previa_num: Optional[str] = None
    comprobacion_previa_num: Optional[str] = None

    # ---------- Normalizaciones (before) ----------
    @field_validator(
        "orden_trabajo_numero",
        "acta_inspeccion_num",
        "acta_notificacion_num",
        "acta_comprobacion_num",
        "acta_clausura_num",
        "acta_decomiso_num",
        "notificacion_previa_num",
        "comprobacion_previa_num",
        mode="before",
    )
    @classmethod
    def normalize_num6(cls, v: Any) -> Any:
        # Regla: actas/OT solo numéricas + zfill(6)
        return _zfill6_if_digit(v)

    @field_validator(
        "rubro_nombre",
        "inspector1",
        "inspector2",
        "inspector3",
        "calle",
        "numero",
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "comprobacion_motivo",
        "oficio_numero",
        "oficio_causa",
        "expediente_numero",
        "notificacion_motivo_1",
        "notificacion_motivo_2",
        "notificacion_motivo_3",
        mode="before",
    )
    @classmethod
    def strip_empty_to_none(cls, v: Any) -> Any:
        return _clean_str(v)

    @field_validator(
        "doc_nro",
        "expediente_numero",
        "oficio_numero",
        "oficio_causa",
        mode="before",
    )
    @classmethod
    def only_digits_fields(cls, v: Any) -> Any:
        # Regla: campos numéricos deben contener solo dígitos
        return _only_digits(v)

    @field_validator("fecha_actuacion", mode="before")
    @classmethod
    def parse_fecha(cls, v: Any) -> date:
        return _parse_fecha(v)

    @field_validator("tipo_actuacion", mode="before")
    @classmethod
    def parse_tipo(cls, v: Any) -> Any:
        return _coerce_catalog_value(
            v,
            CatalogTipoActuacion,
            "tipo",
            strip_prefix="TIPO.",
        )

    @field_validator("contraproducencia", mode="before")
    @classmethod
    def parse_contra(cls, v: Any) -> Any:
        # Regla: si no se carga contraproducencia, por default NO_HUBO
        if v is None or v == "":
            return _coerce_catalog_value(
                "NO_HUBO",
                CatalogContraproducencia,
                "contraproducencia",
            )
        return _coerce_catalog_value(v, CatalogContraproducencia, "contraproducencia")

    @field_validator("comprobacion_motivo", mode="before")
    @classmethod
    def parse_motivo_comprobacion(cls, v: Any) -> Any:
        # Normaliza y valida motivos de comprobación como enum (UI dropdown)
        return _coerce_catalog_value(v, CatalogMotivoComprobacion, "motivo de comprobación")
    @field_validator("calle")
    @classmethod
    def normalize_calle(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        s = v.strip()
        s = re.sub(r"(?i)\bavenida\b", "Av", s)
        s = re.sub(r"(?i)\bav\.\b", "Av", s)
        s = _SPACE_RE.sub(" ", s)
        return s

    # ---------- Helpers ----------
    def fecha_as_date(self) -> date:
        # compat: antes era str + helper; ahora ya es date
        return self.fecha_actuacion

    # ---------- Reglas de negocio (after, errores por celda) ----------
    @model_validator(mode="after")
    def reglas_negocio_base(self) -> "ActuacionGridRowIn":


        field_errors: Dict[str, str] = {}
        # 1.b) Si contraproducencia == NO_HUBO => domicilio obligatorio
        if _matches_catalog(self.contraproducencia, "NO_HUBO"):
            if not self.calle:
                field_errors["calle"] = "Domicilio obligatorio cuando contraproducencia es NO_HUBO."
            if not self.numero:
                field_errors["numero"] = "Domicilio obligatorio cuando contraproducencia es NO_HUBO."



        def has_any_actuation_data() -> bool:
            # datos “relevantes” distintos a OT+fecha+id
            return any(
                [
                    self.tipo_actuacion is not None,
                    self.rubro_nombre,
                    self.inspector1,
                    self.inspector2,
                    self.inspector3,
                    self.calle,
                    self.numero,
                    self.doc_nro,
                    self.contrib_apellido,
                    self.contrib_nombre,
                    self.acta_inspeccion_num,
                    self.acta_notificacion_num,
                    self.acta_comprobacion_num,
                    self.acta_clausura_num,
                    self.acta_decomiso_num,
                    self.decomiso_kilos_total is not None,
                    self.expediente_numero,
                    self.expediente_anio is not None,
                    self.oficio_numero,
                    self.oficio_anio is not None,
                    self.oficio_causa,
                    self.notificacion_previa_num,
                    self.comprobacion_previa_num,
                ]
            )

        # 1) Si la fila está “vacía” (solo OT+fecha), exigir contraproducencia
        # Nota: contraproducencia tiene default NO_HUBO, pero dejamos la regla explícita
        if self.orden_trabajo_numero and not has_any_actuation_data():
            if self.contraproducencia is None:
                field_errors["contraproducencia"] = (
                    "Si solo cargás OT/fecha, debés justificar con contraproducencia."
                )

        # 2) Contribuyente: si hay nombre/apellido, doc obligatorio
        if (self.contrib_apellido or self.contrib_nombre) and not self.doc_nro:
            field_errors["doc_nro"] = "Documento obligatorio si cargás contribuyente."

        # 3) Domicilio: calle y número juntos
        if (self.calle and not self.numero) or (self.numero and not self.calle):
            if not self.calle:
                field_errors["calle"] = "Calle obligatoria si cargás número."
            if not self.numero:
                field_errors["numero"] = "Número obligatorio si cargás calle."

        # 4) Reglas según tipo/contraproducencia
        if self.tipo_actuacion:
            # Si hay tipo: exigir domicilio completo + inspectores
            if not self.calle or not self.numero:
                field_errors["calle"] = "Calle obligatoria cuando hay tipo de actuación."
                field_errors["numero"] = "Número obligatorio cuando hay tipo de actuación."
            # Debe haber al menos un inspector cargado
            if not (self.inspector1 or self.inspector2 or self.inspector3):
                field_errors["inspector1"] = "Debe cargar al menos un inspector."
            # Si hay domicilio con tipo, exigir rubro + doc
            if not self.rubro_nombre:
                field_errors["rubro_nombre"] = "Rubro obligatorio si cargás domicilio."
            if not self.doc_nro:
                field_errors["doc_nro"] = "Documento obligatorio si cargás domicilio."
        else:
            # Si NO hay tipo pero hay contraproducencia + fecha: permitir con calle y número sin contribuyente
            if self.contraproducencia and self.fecha_actuacion:
                if not self.calle or not self.numero:
                    field_errors["calle"] = "Calle obligatoria si cargás contraproducencia."
                    field_errors["numero"] = "Número obligatorio si cargás contraproducencia."

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)
            
        return self
