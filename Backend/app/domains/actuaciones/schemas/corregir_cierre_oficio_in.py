"""Schema de corrección de cierre por reinspección de oficio (GESTIÓN-FIX.2C / 2C.3)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from app.domains.actuaciones.services.actas_quitar_canal_actas_service import (
    normalizar_tipo_acta_canal,
)

ActaCanalQuitarTipo = Literal["INSPECCION", "NOTIFICACION", "COMPROBACION", "CLAUSURA", "DECOMISO"]


class CorregirCierreOficioIn(BaseModel):
  """
  Corrección operativa de una actuación de circuito REINSPECCION_OFICIO ya cerrada.

  ``tipo_actuacion`` es el subtipo destino (puede diferir del persistido en correcciones entre subtipos).
  ``actas_a_quitar`` permite eliminar actas en la misma transacción (GESTIÓN-FIX.3).
  """

  tipo_actuacion: str
  resultado_cumplimiento_oficio: Optional[Literal["CUMPLE", "NO_CUMPLE"]] = None
  contraproducencia: Optional[str] = None
  realizo_nueva_inspeccion: Optional[bool] = None
  actas_a_quitar: Optional[list[ActaCanalQuitarTipo]] = None

  @field_validator("tipo_actuacion", mode="before")
  @classmethod
  def strip_tipo(cls, v: object) -> object:
    if v is None:
      return v
    s = str(v).strip()
    return s or None

  @field_validator("contraproducencia", mode="before")
  @classmethod
  def strip_contra(cls, v: object) -> object:
    if v is None:
      return None
    s = str(v).strip()
    return s or None

  @field_validator("resultado_cumplimiento_oficio", mode="before")
  @classmethod
  def normalize_resultado(cls, v: object) -> object:
    if v is None or v == "":
      return None
    s = str(v).strip().upper()
    if s in ("CUMPLE", "NO_CUMPLE"):
      return s
    raise ValueError("resultado_cumplimiento_oficio debe ser CUMPLE o NO_CUMPLE.")

  @field_validator("actas_a_quitar", mode="before")
  @classmethod
  def normalize_actas_a_quitar(cls, v: object) -> object:
    if v is None:
      return None
    if not isinstance(v, list):
      raise ValueError("actas_a_quitar debe ser una lista de tipos de acta.")
    out: list[str] = []
    seen: set[str] = set()
    for raw in v:
      t = normalizar_tipo_acta_canal(str(raw))
      if t not in seen:
        seen.add(t)
        out.append(t)
    return out or None
