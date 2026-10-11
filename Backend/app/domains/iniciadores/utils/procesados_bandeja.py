"""
Bandeja «Procesados» (Gestión Relevamientos / Denuncias): estados terminales de iniciador_ruta.

No incluye PENDIENTE (reencolados), ANULADO ni soft-delete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.utils.iniciador_estado import normalize_estado_iniciador

# Terminales visibles en Procesados (no vuelven a pendientes operativos ni urgentes por estado).
ESTADOS_BANDEJA_PROCESADOS: tuple[str, ...] = (
    "CUMPLIDO",
    "CERRADO_NO_EXISTE_LOCAL",
    "CERRADO",
)


@dataclass(frozen=True)
class ResultadoProcesadoBandeja:
    """Código estable + etiqueta UI + estado iniciador normalizado."""

    resultado_codigo: str
    resultado_label: str
    iniciador_estado: str


def resolver_resultado_procesado_bandeja(estado_iniciador: Any) -> ResultadoProcesadoBandeja | None:
    """
    Mapea ``estado_iniciador`` a código/label de la bandeja Procesados.

    Retorna None si el estado no pertenece a la bandeja.
    """
    estado = normalize_estado_iniciador(estado_iniciador)
    if not estado or estado not in ESTADOS_BANDEJA_PROCESADOS:
        return None
    if estado == "CUMPLIDO":
        return ResultadoProcesadoBandeja("REALIZADO", "Realizado", estado)
    if estado == "CERRADO_NO_EXISTE_LOCAL":
        return ResultadoProcesadoBandeja("NO_EXISTE_LOCAL", "No existe local", estado)
    if estado == "CERRADO":
        return ResultadoProcesadoBandeja("CERRADO", "Cerrado", estado)
    return ResultadoProcesadoBandeja(estado, estado.replace("_", " ").title(), estado)
