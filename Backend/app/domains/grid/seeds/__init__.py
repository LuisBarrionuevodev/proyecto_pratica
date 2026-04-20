"""Seeds de catálogos expuestos por el dominio grid (p. ej. inspectores)."""

from .inspectores_canonicos import (
    INSPECTORES_CANONICO,
    LEGACY_PLACEHOLDER_LEGAJOS,
    remove_legacy_placeholder_inspectors,
    seed_turnos_base,
    upsert_inspectores_canonicos,
)

__all__ = [
    "INSPECTORES_CANONICO",
    "LEGACY_PLACEHOLDER_LEGAJOS",
    "remove_legacy_placeholder_inspectors",
    "seed_turnos_base",
    "upsert_inspectores_canonicos",
]
