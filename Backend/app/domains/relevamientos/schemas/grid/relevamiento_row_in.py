from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import func
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.database import db
from app.domains.relevamientos.utils.relevador_display import relevador_identity_key_from_nombre
from app.domains.relevamientos.utils.relevador_resolve import (
    parse_relevador_celda_a_nombres,
    resolve_relevador_unico_por_nombre_celda,
)
from app.models import Relevador, Rubro
from app.domains.relevamientos.utils.relevamiento_campos_normalizers import (
    NOMBRE_FANTASIA_MAX_LEN,
    normalizar_angulo_esquina,
    normalizar_nombre_fantasia,
)

_SPACE_RE = re.compile(r"\s+")


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


class RelevamientoGridRowIn(BaseModel):
    """
    Fila proveniente de la grilla de Relevamientos o PUT de gestión.

    Reglas:
    - Exactamente un Relevador (por nombre o id).
    - Calle y Número son obligatorios; Rubro es opcional.
    - Fecha es opcional en carga masiva (PR9.4) y en PUT de gestión; si falta, el servidor
      la asigna al crear o preserva la existente al actualizar.
    """

    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = Field(default=None, ge=1)
    fecha: Optional[date] = None
    relevador: Optional[str] = None
    relevadores: Optional[List[str]] = None
    relevador_id: Optional[int] = None
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

    @field_validator("relevador_id", mode="before")
    @classmethod
    def normalize_relevador_id(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("relevadores", mode="before")
    @classmethod
    def normalize_relevadores_list(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            parsed = parse_relevador_celda_a_nombres(v)
            return parsed or None
        if isinstance(v, list):
            nombres: List[str] = []
            for item in v:
                if isinstance(item, dict):
                    nombre = _clean_str(item.get("nombre"))
                    if nombre:
                        nombres.append(nombre)
                    continue
                s = _clean_str(item)
                if s:
                    nombres.append(s)
            return nombres or None
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

    def relevador_ids_resueltos(self) -> List[int]:
        """Ids únicos de relevador: relevador_ids + relevador_id canónico."""
        ids: List[int] = []
        seen: set[int] = set()
        for raw in self.relevador_ids or []:
            if raw in seen:
                continue
            seen.add(raw)
            ids.append(raw)
        if self.relevador_id is not None and self.relevador_id not in seen:
            ids.append(self.relevador_id)
        return ids

    def relevadores_nombres_resueltos(self) -> List[str]:
        """
        Nombres de relevadores para validación y mapper.
        Prioridad: relevadores > relevador (celda grilla, admite coma).
        """
        if self.relevadores:
            return list(self.relevadores)
        if self.relevador:
            return parse_relevador_celda_a_nombres(self.relevador)
        return []

    @model_validator(mode="after")
    def reglas_negocio_base(self, info: ValidationInfo) -> "RelevamientoGridRowIn":
        field_errors: Dict[str, str] = {}

        allow_missing_relevador = bool(
            info.context and info.context.get("allow_missing_relevador")
        )
        ids = self.relevador_ids_resueltos()
        nombres = self.relevadores_nombres_resueltos() if not ids else []
        if not ids and not nombres and not allow_missing_relevador:
            field_errors["relevador"] = "Debe indicar un relevador."

        if len(ids) > 1:
            field_errors["relevador_ids"] = "El relevador es ambiguo. Seleccioná uno del catálogo."
        if len(nombres) > 1:
            field_errors["relevador"] = "El relevador es ambiguo. Seleccioná uno del catálogo."
        if ids and nombres:
            field_errors["relevador"] = "Indique relevador por id o por nombre, no ambos."

        if not self.calle:
            field_errors["calle"] = "Calle obligatoria."
        if not self.numero:
            field_errors["numero"] = "Número obligatorio."

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)

        if ids and len(ids) == 1:
            row = (
                db.session.query(Relevador.nombre, Relevador.activo)
                .filter(Relevador.id == ids[0])
                .limit(1)
                .first()
            )
            if row is None:
                field_errors["relevador_ids"] = "Relevador inválido."
            elif not row[1]:
                field_errors["relevador_ids"] = f"Relevador inactivo: {row[0]}."
        elif nombres:
            catalog = db.session.query(Relevador).all()
            seen_keys: set[tuple[str, str]] = set()
            for nombre in nombres:
                try:
                    row = resolve_relevador_unico_por_nombre_celda(
                        nombre, requiere_activos=True, catalog=catalog
                    )
                except ValueError as exc:
                    field_errors["relevador"] = str(exc)
                    break
                key = relevador_identity_key_from_nombre(row.nombre)
                if key in seen_keys:
                    field_errors["relevador"] = "Relevador duplicado."
                    break
                seen_keys.add(key)

        if field_errors:
            _raise_field_errors(self.__class__.__name__, field_errors)

        return self

