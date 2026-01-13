"""Compat shim: `app.services.actuaciones.attach.uniqueness` -> `app.domains.actuaciones.attach.uniqueness`."""

from app.domains.actuaciones.attach.uniqueness import (
    asegurar_acta_libre_para_actuacion,
    asegurar_acta_no_usada_en_otra,
)

__all__ = [
    "asegurar_acta_libre_para_actuacion",
    "asegurar_acta_no_usada_en_otra",
]

