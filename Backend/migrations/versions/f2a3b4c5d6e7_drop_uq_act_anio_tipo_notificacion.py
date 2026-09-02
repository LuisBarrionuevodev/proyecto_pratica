"""GESTIÓN-FIX.10A.1: permitir múltiples REINSPECCION por notificación/año.

La unicidad de intentos RN no pertenece a `actuaciones` (cada intento es histórico).
Se elimina `uq_act_anio_tipo_notificacion` y se reemplaza por índice no único de consulta.

Revision ID: f2a3b4c5d6e7
Revises: e5f6a7b8c9d0
Create Date: 2026-09-02

"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "f2a3b4c5d6e7"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

TABLE = "actuaciones"
OLD_UNIQUE = "uq_act_anio_tipo_notificacion"
NEW_INDEX = "ix_act_anio_tipo_notificacion"
INDEX_COLUMNS = ("anio", "tipo", "notificacion_id")


def _drop_uq_act_anio_tipo_notificacion() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    names_to_drop: set[str] = set()

    for uc in inspector.get_unique_constraints(TABLE):
        cols = tuple(uc.get("column_names") or ())
        name = uc.get("name") or ""
        if name == OLD_UNIQUE or cols == INDEX_COLUMNS:
            names_to_drop.add(name)

    for idx in inspector.get_indexes(TABLE):
        name = idx.get("name") or ""
        cols = tuple(idx.get("column_names") or ())
        if name == OLD_UNIQUE or (idx.get("unique") and cols == INDEX_COLUMNS):
            names_to_drop.add(name)

    for name in sorted(names_to_drop):
        try:
            with op.batch_alter_table(TABLE, schema=None) as batch_op:
                batch_op.drop_constraint(name, type_="unique")
        except Exception:
            try:
                op.drop_index(name, table_name=TABLE)
            except Exception:
                op.execute(f"ALTER TABLE {TABLE} DROP INDEX `{name}`")


def _ensure_non_unique_lookup_index() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for idx in inspector.get_indexes(TABLE):
        if idx.get("name") == NEW_INDEX:
            return
    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.create_index(NEW_INDEX, list(INDEX_COLUMNS), unique=False)


def upgrade() -> None:
    _drop_uq_act_anio_tipo_notificacion()
    _ensure_non_unique_lookup_index()


def downgrade() -> None:
    """
    Restaura la unicidad histórica solo si no hay filas duplicadas por
    (anio, tipo, notificacion_id). Si ya existen múltiples intentos RN válidos,
    el downgrade fallará hasta limpiar o consolidar datos manualmente.
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    for idx in inspector.get_indexes(TABLE):
        if idx.get("name") == NEW_INDEX and not idx.get("unique"):
            with op.batch_alter_table(TABLE, schema=None) as batch_op:
                batch_op.drop_index(NEW_INDEX)
            break

    with op.batch_alter_table(TABLE, schema=None) as batch_op:
        batch_op.create_unique_constraint(OLD_UNIQUE, list(INDEX_COLUMNS))
