"""Política de edición de domicilio (STAB-7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModoEdicionDomicilio = Literal[
    "EDITAR_MISMA_FILA",
    "CREAR_NUEVO",
    "REASIGNAR_EXISTENTE",
    "BLOQUEAR",
]


@dataclass(frozen=True)
class EditDomicilioPolicy:
    """
    Decisión centralizada para edición de domicilio operativo.

    Attributes:
        modo: acción a ejecutar.
        motivo: texto legible para logs/errores.
        propagar_a_iniciadores: si el caller debe invocar propagación PR2.
        requiere_geocode_refresh: si calle/número/barrio relevante cambió.
        domicilio_id_objetivo: id a usar (misma fila, existente o nuevo tras apply).
    """

    modo: ModoEdicionDomicilio
    motivo: str
    propagar_a_iniciadores: bool = False
    requiere_geocode_refresh: bool = False
    domicilio_id_objetivo: int | None = None
