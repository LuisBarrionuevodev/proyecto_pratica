"""
Expedientes «vigentes»: ``deleted_at IS NULL``.

Centraliza el filtro para evitar validaciones que cuenten filas soft-deleted como si fueran activas.
"""

from __future__ import annotations

from sqlalchemy.orm import Query

from app.models import Expediente


def expedientes_vigentes(query: Query) -> Query:
    """
    Restringe una query existente sobre ``Expediente`` a filas no borradas en soft delete.

    Parámetros:
        query: Query SQLAlchemy sobre ``Expediente``.

    Retorno:
        La misma query encadenada con ``deleted_at IS NULL``.
    """
    return query.filter(Expediente.deleted_at.is_(None))
