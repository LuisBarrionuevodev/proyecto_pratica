"""
Seed idempotente de relevadores para QA y operación inicial.
"""

from __future__ import annotations

from app.models import Relevador

RELEVADORES_CANONICO: tuple[str, ...] = (
    "Fabian Esquivel",
)


def upsert_relevadores_canonicos(session) -> tuple[int, int, int]:
    """
    Inserta o actualiza relevadores canónicos por nombre.

    Returns:
        Tupla (creados, actualizados, sin_cambio).
    """
    created = updated = skipped = 0
    for nombre in RELEVADORES_CANONICO:
        existing = session.query(Relevador).filter(Relevador.nombre == nombre).first()
        if existing is None:
            session.add(Relevador(nombre=nombre, activo=True))
            created += 1
        elif not existing.activo:
            existing.activo = True
            session.add(existing)
            updated += 1
        else:
            skipped += 1
    return created, updated, skipped
