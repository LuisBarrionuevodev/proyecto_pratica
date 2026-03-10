"""add notificacion timing fields

Revision ID: c4d9f2a1b8e7
Revises: b960c9de1bbb
Create Date: 2026-03-10 16:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4d9f2a1b8e7"
down_revision = "b960c9de1bbb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notificacion",
        sa.Column("plazo_dias", sa.Integer(), nullable=True, server_default="5"),
    )
    op.add_column(
        "notificacion",
        sa.Column("prorroga_dias", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "notificacion",
        sa.Column("fecha_notificacion", sa.Date(), nullable=True),
    )
    op.add_column(
        "notificacion",
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_notificacion_fecha_notificacion",
        "notificacion",
        ["fecha_notificacion"],
        unique=False,
    )
    op.create_index(
        "ix_notificacion_fecha_vencimiento",
        "notificacion",
        ["fecha_vencimiento"],
        unique=False,
    )

    # Backfill defaults de plazo/prórroga
    op.execute("UPDATE notificacion SET plazo_dias = 5 WHERE plazo_dias IS NULL")
    op.execute("UPDATE notificacion SET prorroga_dias = 0 WHERE prorroga_dias IS NULL")

    # fecha_notificacion: tomar la fecha mínima de actuaciones asociadas a la notificación.
    op.execute(
        """
        UPDATE notificacion n
        LEFT JOIN (
            SELECT notificacion_id, MIN(fecha) AS min_fecha
            FROM actuaciones
            WHERE notificacion_id IS NOT NULL
            GROUP BY notificacion_id
        ) a ON a.notificacion_id = n.id
        SET n.fecha_notificacion = COALESCE(a.min_fecha, CURRENT_DATE)
        WHERE n.fecha_notificacion IS NULL
        """
    )

    # fecha_vencimiento = fecha_notificacion + plazo_dias + prorroga_dias
    op.execute(
        """
        UPDATE notificacion
        SET fecha_vencimiento = DATE_ADD(
            fecha_notificacion,
            INTERVAL (COALESCE(plazo_dias, 5) + COALESCE(prorroga_dias, 0)) DAY
        )
        WHERE fecha_notificacion IS NOT NULL
        """
    )

    op.alter_column(
        "notificacion",
        "plazo_dias",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="5",
    )
    op.alter_column(
        "notificacion",
        "prorroga_dias",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )


def downgrade() -> None:
    op.drop_index("ix_notificacion_fecha_vencimiento", table_name="notificacion")
    op.drop_index("ix_notificacion_fecha_notificacion", table_name="notificacion")
    op.drop_column("notificacion", "fecha_vencimiento")
    op.drop_column("notificacion", "fecha_notificacion")
    op.drop_column("notificacion", "prorroga_dias")
    op.drop_column("notificacion", "plazo_dias")
