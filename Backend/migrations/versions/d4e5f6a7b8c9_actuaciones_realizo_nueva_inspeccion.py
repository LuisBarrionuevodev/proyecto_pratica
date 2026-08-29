"""actuaciones.realizo_nueva_inspeccion (GESTIÓN-FIX.2C).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _tiene_actas_inspeccion_normal(connection, actuacion_id: int) -> bool:
    """True si hay actas/datos inequívocos de inspección normal en la actuación."""
    row = connection.execute(
        sa.text(
            """
            SELECT
                a.notificacion_id,
                i.id AS inspeccion_id,
                c.id AS comp_id,
                cl.id AS clausura_id,
                d.id AS decomiso_id,
                (SELECT COUNT(*) FROM notificacion_motivo nm
                 WHERE nm.notificacion_id = a.notificacion_id) AS motivos_cnt
            FROM actuaciones a
            LEFT JOIN inspeccion i ON i.actuacion_id = a.id
            LEFT JOIN comprobacion c ON c.id = a.comprobacion_id
            LEFT JOIN clausura cl ON cl.actuacion_id = a.id
            LEFT JOIN decomiso d ON d.actuacion_id = a.id
            WHERE a.id = :aid
            """
        ),
        {"aid": actuacion_id},
    ).mappings().first()
    if not row:
        return False
    if row["inspeccion_id"]:
        return True
    if row["notificacion_id"] and int(row["motivos_cnt"] or 0) > 0:
        return True
    if row["comp_id"]:
        return True
    if row["clausura_id"]:
        return True
    if row["decomiso_id"]:
        return True
    return False


def _backfill_realizo_nueva_inspeccion(connection) -> None:
    """Backfill conservador solo para VERIFICAR E INFORMAR."""
    rows = connection.execute(
        sa.text(
            """
            SELECT id, tipo, contraproducencia
            FROM actuaciones
            WHERE UPPER(REPLACE(REPLACE(COALESCE(tipo, ''), '_', ' '), '/', ' ')) LIKE '%VERIFICAR%INFORMAR%'
            """
        )
    ).mappings().all()
    for row in rows:
        aid = int(row["id"])
        if _tiene_actas_inspeccion_normal(connection, aid):
            connection.execute(
                sa.text(
                    "UPDATE actuaciones SET realizo_nueva_inspeccion = TRUE WHERE id = :aid"
                ),
                {"aid": aid},
            )
            continue
        contra = (row["contraproducencia"] or "").strip()
        if not contra:
            connection.execute(
                sa.text(
                    "UPDATE actuaciones SET realizo_nueva_inspeccion = FALSE WHERE id = :aid"
                ),
                {"aid": aid},
            )
        # Caso ambiguo (contra sin actas): permanece NULL


def upgrade() -> None:
    op.add_column(
        "actuaciones",
        sa.Column("realizo_nueva_inspeccion", sa.Boolean(), nullable=True),
    )
    bind = op.get_bind()
    _backfill_realizo_nueva_inspeccion(bind)


def downgrade() -> None:
    op.drop_column("actuaciones", "realizo_nueva_inspeccion")
