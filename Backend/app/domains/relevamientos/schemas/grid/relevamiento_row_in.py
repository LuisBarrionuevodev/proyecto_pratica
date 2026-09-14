from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import func
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.database import db
from app.models import Relevador, Rubro
from app.domains.relevamientos.utils.relevamiento_campos_normalizers import (
    NOMBRE_FANTASIA_MAX_LEN,
    normalizar_angulo_esquina,
    normalizar_nombre_fantasia,
)

_SPACE_RE = re.compile(r"\s+")
_RELEVADOR_SEP_RE = re.compile(r"[;,]")


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _upper_norm(s: str) -> str:
    s = s.strip().upper()
    s = s.replace("_", " ")
    s = _SPACE_RE.sub(" ", s)
    return s


def _parse_fecha(v: Any) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    s = _clean_str(v)
    if not s:
        raise ValueError("Fecha requerida.")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except ValueError as e:
        raise ValueError("Formato de fecha inválido. Use DD/MM/YYYY o YYYY-MM-DD.") from e


def _coerce_catalog_value(
    value: Any,
    model_cls: Type[db.Model],
    field_label: str,
) -> Optional[str]:
    s = _clean_str(value)
    if not s:
        return None
    s_norm = _upper_norm(s)
    row = (
        db.session.query(model_cls.nombre)
        .filter(func.replace(func.upper(model_cls.nombre), "_", " ") == s_norm)
        .limit(1)
        .first()
    )
    if row is None:
        raise ValueError(f"{field_label} inválido.")
    return row[0]


def _raise_field_errors(model_name: str, field_errors: Dict[str, str]) -> None:
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


def _parse_relevador_nombres(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            s = _clean_str(item)
            if s:
                out.append(s)
        return out
    s = _clean_str(value)
    if not s:
        return []
    parts = [p.strip() for p in _RELEVADOR_SEP_RE.split(s) if p.strip()]
    return parts or [s]


class RelevamientoGridRowIn(BaseModel):
    """
    Fila proveniente de la grilla de Relevamientos o PUT de gestión.

    Reglas:
    - Al menos un Relevador (por nombres o ids).
    - Calle, Número y Rubro son obligatorios.
    - Fecha es opcional en carga masiva (PR9.4); si falta, el servidor la asigna al guardar.
    """

    id: Optional[int] = Field(default=None, ge=1)
    fecha: Optional[date] = None
    relevador: Optional[str] = None
    relevadores: Optional[List[str]] = None
    relevador_ids: Optional[List[int]] = None
    calle: str
    numero: str
    numero_tipo: Optional[str] = None
    rubro: Optional[str] = None
    nombre_fantasia: Optional[str] = Field(default=None, max_length=NOMBRE_FANTASIA_MAX_LEN)
    angulo_esquina: Optional[str] = None
    turno: Optional[str] = None
    esta_abierto: Optional[bool] = None

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

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v: Any) -> Optional[date]:
        if v is None or v == "":
            return None
        return _parse_fecha(v)

    @field_validator("relevador", mode="before")
    @classmethod
    def strip_relevador(cls, v: Any) -> Any:
        return _clean_str(v)

    @field_validator("relevadores", mode="before")
    @classmethod
    def normalize_relevadores_list(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            parsed = _parse_relevador_nombres(v)
            return parsed or None
        if isinstance(v, list):
            return _parse_relevador_nombres(v)
        raise ValueError("relevadores debe ser una lista de strings.")

    @field_validator("relevador_ids", mode="before")
    @classmethod
    def normalize_relevador_ids(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if not isinstance(v, list):
            raise ValueError("relevador_ids debe ser una lista de enteros.")
        out: List[int] = []
        seen: set[int] = set()
        for item in v:
            if item is None or item == "":
                continue
            i = int(item)
            if i in seen:
                continue
            seen.add(i)
            out.append(i)
        return out or None

    @field_validator("calle", "numero", "rubro", "nombre_fantasia", mode="before")
    @classmethod
    def strip_empty_to_none(cls, v: Any) -> Any:
        return _clean_str(v)

    @field_validator("nombre_fantasia")
    @classmethod
    def validate_nombre_fantasia(cls, v: Optional[str]) -> Optional[str]:
        return normalizar_nombre_fantasia(v)

    @field_validator("angulo_esquina", mode="before")
    @classmethod
    def validate_angulo_esquina(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        return normalizar_angulo_esquina(v)

    @field_validator("turno", mode="before")
    @classmethod
    def parse_turno(cls, v: Any) -> Optional[str]:
        s = _clean_str(v)
        if not s:
            return None
        u = s.strip().upper().replace("Ñ", "N")
        if u in ("MANIANA", "MANANA"):
            return "MANIANA"
        if u == "TARDE":
            return "TARDE"
        raise ValueError("Turno inválido (Mañana/MANIANA o Tarde/TARDE, o vacío).")

    @field_validator("esta_abierto", mode="before")
    @classmethod
    def parse_esta_abierto(cls, v: Any) -> Optional[bool]:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("sí", "si", "yes", "true", "1", "s"):
            return True
        if s in ("no", "false", "0", "n"):
            return False
        return None

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

    @field_validator("rubro")
    @classmethod
    def validate_rubro(cls, v: Optional[str]) -> Optional[str]:
        return _coerce_catalog_value(v, Rubro, "Rubro")

    def relevadores_nombres_resueltos(self) -> List[str]:
        """
        Nombres de relevadores para validación y mapper.
        Prioridad: relevadores > relevador (celda grilla, admite coma).
        """
        if self.relevadores:
            return list(self.relevadores)
        if self.relevador:
            return _parse_relevador_nombres(self.relevador)
        return []

    @model_validator(mode="after")
    def reglas_negocio_base(self) -> "RelevamientoGridRowIn":
        field_errors: Dict[str, str] = {}

        tiene_ids = bool(self.relevador_ids)
        nombres = self.relevadores_nombres_resueltos()
        if not tiene_ids and not nombres:
            field_errors["relevador"] = "Relevador obligatorio."

        if not self.calle:
            field_errors["calle"] = "Calle obligatoria."
        if not self.numero:
            field_errors["numero"] = "Número obligatorio."
        if not self.rubro:
            field_errors["rubro"] = "Rubro obligatorio."

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)

        if nombres:
            seen_norm: set[str] = set()
            for nombre in nombres:
                norm = _upper_norm(nombre)
                row = (
                    db.session.query(Relevador.nombre, Relevador.activo)
                    .filter(func.replace(func.upper(Relevador.nombre), "_", " ") == norm)
                    .limit(1)
                    .first()
                )
                if row is None:
                    field_errors["relevador"] = f"Relevador inválido: {nombre}."
                    break
                if not row[1]:
                    field_errors["relevador"] = f"Relevador inactivo: {row[0]}."
                    break
                if norm in seen_norm:
                    field_errors["relevador"] = "Relevador duplicado."
                    break
                seen_norm.add(norm)

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)

        return self
