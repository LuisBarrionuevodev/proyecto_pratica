"""ACT-HIST.5 — sin expediente envío + materialización diferida de oficio.

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-09-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r3"
branch_labels = None
depends_on = None

_MAT_ESTADO_ENUM = sa.Enum(
    "MATERIALIZADO",
    "PENDIENTE_DOMICILIO",
    "PENDIENTE_MATERIALIZACION",
    name="iniciador_materializacion_estado_enum",
)

_TIPOS_INI_OFICIO = (
    "REINSPECCION_OFICIO",
    "VERIFICAR_INFORMAR_OFICIO",
    "RATIFICACION_CLAUSURA_OFICIO",
    "RATIFICACION_DECOMISO_OFICIO",
)


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _backfill_oficio_materializacion_estado() -> dict[str, int]:
    bind = op.get_bind()
    counts = {"MATERIALIZADO": 0, "PENDIENTE_DOMICILIO": 0, "PENDIENTE_MATERIALIZACION": 0}
    tipos_sql = ", ".join(f"'{t}'" for t in _TIPOS_INI_OFICIO)

    rows = bind.execute(
        text(
            f"""
            SELECT o.id AS oficio_id, o.comprobacion_id
            FROM oficio o
            WHERE o.deleted_at IS NULL
            """
        )
    ).fetchall()

    for row in rows:
        oficio_id = int(row.oficio_id)
        comprobacion_id = row.comprobacion_id
        has_ini = bind.execute(
            text(
                f"""
                SELECT 1 FROM iniciador_ruta i
                WHERE i.oficio_id = :oid
                  AND i.deleted_at IS NULL
                  AND i.tipo_iniciador IN ({tipos_sql})
                LIMIT 1
                """
            ),
            {"oid": oficio_id},
        ).first()
        if has_ini:
            estado = "MATERIALIZADO"
        else:
            act_row = bind.execute(
                text(
                    """
                    SELECT a.domicilio_id
                    FROM actuaciones a
                    WHERE a.comprobacion_id = :cid
                    ORDER BY a.id DESC
                    LIMIT 1
                    """
                ),
                {"cid": comprobacion_id},
            ).first()
            domicilio_id = act_row.domicilio_id if act_row else None
            if domicilio_id is None:
                estado = "PENDIENTE_DOMICILIO"
            else:
                estado = "PENDIENTE_MATERIALIZACION"
        counts[estado] += 1
        bind.execute(
            text(
                """
                UPDATE oficio
                SET iniciador_materializacion_estado = :estado
                WHERE id = :oid
                """
            ),
            {"estado": estado, "oid": oficio_id},
        )
    return counts


def upgrade() -> None:
    if not _column_exists("comprobacion", "sin_expediente_envio"):
        with op.batch_alter_table("comprobacion", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "sin_expediente_envio",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
            batch_op.add_column(
                sa.Column("sin_expediente_envio_declarado_at", sa.DateTime(), nullable=True)
            )
            batch_op.add_column(
                sa.Column("sin_expediente_envio_declarado_by_user_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_comprobacion_sin_exp_decl_user",
                "users",
                ["sin_expediente_envio_declarado_by_user_id"],
                ["id"],
                ondelete="SET NULL",
                onupdate="CASCADE",
            )

    if not _column_exists("oficio", "iniciador_materializacion_estado"):
        _MAT_ESTADO_ENUM.create(op.get_bind(), checkfirst=True)
        with op.batch_alter_table("oficio", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "iniciador_materializacion_estado",
                    _MAT_ESTADO_ENUM,
                    nullable=False,
                    server_default="MATERIALIZADO",
                )
            )

    op.execute(
        text("UPDATE comprobacion SET sin_expediente_envio = 0 WHERE sin_expediente_envio IS NULL")
    )
    _backfill_oficio_materializacion_estado()


def downgrade() -> None:
    with op.batch_alter_table("oficio", schema=None) as batch_op:
        batch_op.drop_column("iniciador_materializacion_estado")
    _MAT_ESTADO_ENUM.drop(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("comprobacion", schema=None) as batch_op:
        batch_op.drop_constraint("fk_comprobacion_sin_exp_decl_user", type_="foreignkey")
        batch_op.drop_column("sin_expediente_envio_declarado_by_user_id")
        batch_op.drop_column("sin_expediente_envio_declarado_at")
        batch_op.drop_column("sin_expediente_envio")
