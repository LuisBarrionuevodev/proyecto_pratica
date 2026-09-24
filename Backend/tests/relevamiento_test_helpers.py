"""Helpers compartidos para tests de relevamientos (dominio Relevador)."""

from __future__ import annotations

from uuid import uuid4

from app.database import db
from app.models import Relevador, Rubro


def _migration_relevadores_aplicada() -> bool:
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    return insp.has_table("relevador")


def require_relevadores_migration():
    import pytest

    if not _migration_relevadores_aplicada():
        pytest.skip("Requiere migración RELEVADORES.1 (relevador / relevamiento_relevador)")


def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def get_or_create_test_relevador(nombre: str = "Fabian Esquivel") -> Relevador:
    """Obtiene o crea un relevador activo para tests."""
    row = Relevador.query.filter(Relevador.nombre == nombre).first()
    if row is None:
        row = Relevador(nombre=nombre, activo=True)
        db.session.add(row)
        db.session.commit()
    elif not row.activo:
        row.activo = True
        db.session.add(row)
        db.session.commit()
    return row


def get_test_rubro() -> Rubro:
    rub = Rubro.query.first()
    if rub is None:
        raise RuntimeError("Se requiere al menos un rubro en la BD de test")
    return rub


def relevador_y_rubro() -> tuple[Relevador, Rubro]:
    """Par canónico Relevador + Rubro para fixtures de alta de relevamiento."""
    return get_or_create_test_relevador(), get_test_rubro()


def relevadores_nombres_default() -> list[str]:
    """Nombre canónico del seed QA (Fabian Esquivel)."""
    return [get_or_create_test_relevador().nombre]


def relevamiento_create_payload(
    *,
    calle: str,
    numero: str,
    rubro: str,
    relevador_nombre: str | None = None,
    relevadores_nombres: list[str] | None = None,
    fecha: str | None = "2026-03-10",
    **extra,
) -> dict:
    nombres = relevadores_nombres or ([relevador_nombre] if relevador_nombre else [])
    out = {
        "relevadores_nombres": nombres,
        "domicilio": {"calle": calle, "numero": numero},
        "rubro_nombre": rubro,
        **extra,
    }
    if fecha is not None:
        out["fecha"] = fecha
    return out


def relevamiento_grid_row(
    *,
    calle: str,
    numero: str,
    rubro: str,
    relevador: str,
    fecha: str | None = None,
) -> dict:
    raw = {
        "relevador": relevador,
        "calle": calle,
        "numero": numero,
        "rubro": rubro,
    }
    if fecha is not None:
        raw["fecha"] = fecha
    return raw
