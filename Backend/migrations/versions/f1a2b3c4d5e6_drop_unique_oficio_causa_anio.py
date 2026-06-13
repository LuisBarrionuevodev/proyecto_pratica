"""STAB-2: eliminar unicidad (causa, anio) en oficio.

La causa puede repetirse en varios oficios del mismo año.
Se mantiene la unicidad por (numero_oficio, anio) en filas activas si existe.

Revision ID: f1a2b3c4d5e6
Revises: c9d8e7f6a5b4
Create Date: 2026-06-02

"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "f1a2b3c4d5e6"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def _drop_causa_anio_uniqueness() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table = "oficio"

    names_to_drop = set()
    for uc in inspector.get_unique_constraints(table):
        cols = tuple(uc.get("column_names") or ())
        if cols == ("causa", "anio") or uc.get("name") == "uq_of_causa_anio":
            names_to_drop.add(uc["name"])

    for idx in inspector.get_indexes(table):
        name = idx.get("name") or ""
        cols = tuple(idx.get("column_names") or ())
        if name == "uq_of_causa_anio" or (idx.get("unique") and cols == ("causa", "anio")):
            names_to_drop.add(name)

    for name in sorted(names_to_drop):
        try:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_constraint(name, type_="unique")
        except Exception:
            op.drop_index(name, table_name=table)

    col_names = {c["name"] for c in inspector.get_columns(table)}
    for col in ("uq_causa_anio_activo", "causa_anio_activo"):
        if col in col_names:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_column(col)


def upgrade() -> None:
    _drop_causa_anio_uniqueness()


def downgrade() -> None:
    """No se restaura uq_of_causa_anio: la regla de negocio ya no aplica."""
    pass
