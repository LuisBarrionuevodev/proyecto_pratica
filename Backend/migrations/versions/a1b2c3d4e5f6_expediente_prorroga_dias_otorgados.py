"""expediente: prorroga_dias_otorgados por fila PRORROGA_NOTIFICACION

Revision ID: a1b2c3d4e5f6
Revises: c378dcc33cd0
Create Date: 2026-03-30

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "c378dcc33cd0"
branch_labels = None
depends_on = None


def _expediente_column_names(bind) -> set[str]:
    return {c["name"] for c in inspect(bind).get_columns("expediente")}


def _backfill_prorroga_otorgados(bind) -> None:
    noti_rows = bind.execute(
        text(
            """
            SELECT DISTINCT e.notificacion_id
            FROM expediente e
            WHERE e.tipo_expediente = 'PRORROGA_NOTIFICACION'
              AND e.deleted_at IS NULL
              AND e.notificacion_id IS NOT NULL
            """
        )
    ).fetchall()

    for (notificacion_id,) in noti_rows:
        total_row = bind.execute(
            text("SELECT prorroga_dias FROM notificacion WHERE id = :nid"),
            {"nid": notificacion_id},
        ).fetchone()
        if total_row is None:
            continue
        total = int(total_row[0] or 0)

        ex_rows = bind.execute(
            text(
                """
                SELECT id FROM expediente
                WHERE notificacion_id = :nid
                  AND tipo_expediente = 'PRORROGA_NOTIFICACION'
                  AND deleted_at IS NULL
                ORDER BY id ASC
                """
            ),
            {"nid": notificacion_id},
        ).fetchall()
        ids = [r[0] for r in ex_rows]
        if not ids:
            continue
        if len(ids) == 1:
            bind.execute(
                text("UPDATE expediente SET prorroga_dias_otorgados = :d WHERE id = :eid"),
                {"d": total, "eid": ids[0]},
            )
        else:
            for eid in ids[:-1]:
                bind.execute(
                    text("UPDATE expediente SET prorroga_dias_otorgados = 0 WHERE id = :eid"),
                    {"eid": eid},
                )
            bind.execute(
                text("UPDATE expediente SET prorroga_dias_otorgados = :d WHERE id = :eid"),
                {"d": total, "eid": ids[-1]},
            )


def upgrade() -> None:
    bind = op.get_bind()
    cols = _expediente_column_names(bind)
    if "prorroga_dias_otorgados" not in cols:
        op.add_column(
            "expediente",
            sa.Column("prorroga_dias_otorgados", sa.Integer(), nullable=True),
        )
        _backfill_prorroga_otorgados(bind)
    # Si la columna ya existía (p. ej. DDL manual o entorno de tests), no se pisa data; Alembic igual avanza la revisión.


def downgrade() -> None:
    bind = op.get_bind()
    if "prorroga_dias_otorgados" in _expediente_column_names(bind):
        op.drop_column("expediente", "prorroga_dias_otorgados")
