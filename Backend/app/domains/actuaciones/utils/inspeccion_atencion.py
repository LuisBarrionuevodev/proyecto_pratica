"""V1.1-INSPECCION.1 — carácter de quien atendió y contrato de residuos (Acta de Inspección)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import ValidationError

CARACTER_PERSONA_ATENDIO_VALORES = frozenset({"TITULAR", "ENCARGADO", "EMPLEADO", "OTRO"})
INSPECCION_ATENCION_PAYLOAD_KEYS = (
    "caracter_persona_atendio",
    "posee_contrato_retiro_residuos_solidos_urbanos",
)
MSG_CARACTER_PERSONA_ATENDIO_INVALIDO = (
    "Carácter inválido. Use TITULAR, ENCARGADO, EMPLEADO u OTRO."
)
MSG_CONTRATO_RESIDUOS_INVALIDO = "Debe ser true, false o vacío."
MSG_ATENCION_REQUIERE_ACTA_INSPECCION = "Estos datos requieren un acta de inspección."


def normalize_caracter_persona_atendio(v: Any) -> Optional[str]:
    """Normaliza el carácter; vacío → None. Rechaza valores fuera del conjunto."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().upper()
        if not s:
            return None
        if s not in CARACTER_PERSONA_ATENDIO_VALORES:
            raise ValueError(MSG_CARACTER_PERSONA_ATENDIO_INVALIDO)
        return s
    raise ValueError(MSG_CARACTER_PERSONA_ATENDIO_INVALIDO)


def normalize_bool_nullable(v: Any) -> Optional[bool]:
    """Normaliza booleano opcional; vacío → None."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if not s:
            return None
        if s in ("true", "1", "si", "sí", "yes"):
            return True
        if s in ("false", "0", "no"):
            return False
    raise ValueError(MSG_CONTRATO_RESIDUOS_INVALIDO)


def caracter_persona_atendio_to_str(value: Any) -> Optional[str]:
    """Serializa el carácter persistido (string o enum) a str o None."""
    if value is None:
        return None
    raw = getattr(value, "value", None)
    if raw is not None:
        s = str(raw).strip()
        return s or None
    s = str(value).strip()
    return s or None


def inspeccion_atencion_grid_fields(inspeccion: Any | None) -> dict[str, Any]:
    """Campos planos de atención para presenters de grilla / detalle / Completar trabajo."""
    if inspeccion is None:
        return {
            "caracter_persona_atendio": None,
            "posee_contrato_retiro_residuos_solidos_urbanos": None,
        }
    return {
        "caracter_persona_atendio": caracter_persona_atendio_to_str(
            getattr(inspeccion, "caracter_persona_atendio", None)
        ),
        "posee_contrato_retiro_residuos_solidos_urbanos": getattr(
            inspeccion, "posee_contrato_retiro_residuos_solidos_urbanos", None
        ),
    }


def raise_atencion_requiere_acta(keys: list[str]) -> None:
    """422 por campo: los datos de atención exigen un Acta de Inspección."""
    errs = [
        {
            "type": "value_error",
            "loc": (key,),
            "msg": "Value error",
            "input": None,
            "ctx": {"error": MSG_ATENCION_REQUIERE_ACTA_INSPECCION},
        }
        for key in keys
    ]
    raise ValidationError.from_exception_data("InspeccionAtencion", errs)
