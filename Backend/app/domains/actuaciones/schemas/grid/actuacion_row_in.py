from __future__ import annotations

import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import func
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

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
    Fila del canal **CargarActuacion** (grilla Glide / MRT).

    Incluye actas operativas del día y datos de actuación. Columnas `expediente_*` / `oficio_*` existen
    solo como keys de grilla heredadas: si vienen con datos, el validador las rechaza (expediente de
    comprobación y oficio se cargan solo por **Esperando expediente** / **Esperando oficio**).

    `ec5_uuid` no forma parte del contrato de este canal: se ignora si el cliente lo envía.
    """

    model_config = ConfigDict(extra="ignore")

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
    nombre_local: Optional[str] = None
    tipo_actuacion: Optional[str] = None
    contraproducencia: Optional[str] = None
    # True cuando el usuario borró contraproducencia en edición (PUT no debe omitir el clear).
    limpiar_contraproducencia: bool = False

    # Inspectores (catálogo DB)
    # Lista canónica para persistir (sin tope). Si viene, tiene prioridad sobre inspector1/2/3.
    inspectores: Optional[List[str]] = None
    inspector1: Optional[str] = None
    inspector2: Optional[str] = None
    inspector3: Optional[str] = None

    # Domicilio
    calle: Optional[str] = None
    numero: Optional[str] = None  # permite str libre (ej: esquina, s/n)
    numero_tipo: Optional[str] = None

    # Contribuyente
    doc_nro: Optional[str] = None
    contrib_apellido: Optional[str] = None
    contrib_nombre: Optional[str] = None
    razon_social: Optional[str] = None

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

    # Columnas legacy de grilla; con valor → error (ver reglas_negocio_base)
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
        "nombre_local",
        "inspector1",
        "inspector2",
        "inspector3",
        "calle",
        "numero",
        "doc_nro",
        "contrib_apellido",
        "contrib_nombre",
        "razon_social",
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

    @field_validator("inspectores", mode="before")
    @classmethod
    def normalize_inspectores_list(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("inspectores debe ser una lista de strings.")
        out: List[str] = []
        for item in v:
            s = _clean_str(item)
            if s:
                out.append(s)
        return out

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
        # STAB-4: sin default NO_HUBO; vacío → None (no pisa valor existente en update).
        if v is None or v == "":
            return None
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

    def inspectores_resueltos(self) -> List[str]:
        """
        Lista de nombres de inspectores para validación y mapper.

        Si ``inspectores`` viene informado (incluye lista vacía), es la fuente canónica.
        Si es ``None``, se derivan de inspector1/2/3 (compatibilidad grilla / Excel).
        """
        if self.inspectores is not None:
            return list(self.inspectores)
        return [x for x in [self.inspector1, self.inspector2, self.inspector3] if x]

    @field_validator("numero_tipo", mode="before")
    @classmethod
    def normalize_numero_tipo(cls, v: Any) -> Optional[str]:
        s = _clean_str(v)
        if not s:
            return None
        s = s.strip().upper()
        if s in ("NUMERO", "ESQUINA", "OTRO"):
            return s
        raise ValueError("numero_tipo inválido.")

    # ---------- Reglas de negocio (after, errores por celda) ----------
    @model_validator(mode="after")
    def reglas_negocio_base(self) -> "ActuacionGridRowIn":


        field_errors: Dict[str, str] = {}
        # Canal actas: prohibido cargar aquí oficio ni expediente administrativo
        if self.expediente_numero or self.expediente_anio is not None:
            field_errors["expediente_numero"] = (
                "El canal de carga de actas no admite expediente. "
                "Use el flujo específico de expediente (Esperando expediente)."
            )
        if self.oficio_numero or self.oficio_anio is not None or self.oficio_causa:
            field_errors["oficio_numero"] = (
                "El canal de carga de actas no admite oficio. "
                "Use el flujo específico de oficio (Esperando oficio)."
            )
        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)

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
                    bool(self.inspectores_resueltos()),
                    self.calle,
                    self.numero,
                    self.doc_nro,
                    self.contrib_apellido,
                    self.contrib_nombre,
                    self.razon_social,
                    self.acta_inspeccion_num,
                    self.acta_notificacion_num,
                    self.acta_comprobacion_num,
                    self.acta_clausura_num,
                    self.acta_decomiso_num,
                    self.decomiso_kilos_total is not None,
                    self.notificacion_previa_num,
                    self.comprobacion_previa_num,
                ]
            )

        # 1) Si la fila está “vacía” (solo OT+fecha), exigir contraproducencia explícita
        if self.orden_trabajo_numero and not has_any_actuation_data():
            if self.contraproducencia is None:
                field_errors["contraproducencia"] = (
                    "Si solo cargás OT/fecha, debés elegir una contraproducencia (p. ej. NO_HUBO)."
                )

        # 2) Contribuyente: si hay nombre/apellido/razón social, doc obligatorio
        if (self.contrib_apellido or self.contrib_nombre or self.razon_social) and not self.doc_nro:
            field_errors["doc_nro"] = "Documento obligatorio si cargás contribuyente."

        # 3) Domicilio: calle y número juntos
        if (self.calle and not self.numero) or (self.numero and not self.calle):
            if not self.calle:
                field_errors["calle"] = "Calle obligatoria si cargás número."
            if not self.numero:
                field_errors["numero"] = "Número obligatorio si cargás calle."

        # 4) Reglas según tipo/contraproducencia
        if self.tipo_actuacion:
            # Debe haber al menos un inspector cargado
            if not self.inspectores_resueltos():
                field_errors["inspectores"] = "Debe cargar al menos un inspector."
            # PR7.15d: en edición (id), omitir calle/número/rubro/doc si no se envía domicilio geo.
            envia_domicilio_geo = bool(self.calle or self.numero)
            exige_domicilio_completo = envia_domicilio_geo or self.id is None
            if exige_domicilio_completo:
                if not self.calle or not self.numero:
                    field_errors["calle"] = "Calle obligatoria cuando hay tipo de actuación."
                    field_errors["numero"] = "Número obligatorio cuando hay tipo de actuación."
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

        # Notificación: acta ⇒ al menos un motivo
        if self.acta_notificacion_num:
            if not any([self.notificacion_motivo_1, self.notificacion_motivo_2, self.notificacion_motivo_3]):
                field_errors["notificacion_motivo_1"] = "La notificación requiere al menos un motivo."

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)
            
        return self
