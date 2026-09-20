"""ACTA-INSPECCION-HABILITACION.1 — checklist tipado ESTADO/SI_NO + TIENE_HABILITACION.

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-09-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "l7m8n9o0p1q2"
down_revision = "k6l7m8n9o0p1"
branch_labels = None
depends_on = None

_TIPO_RESPUESTA_ENUM = sa.Enum("ESTADO", "SI_NO", name="item_acta_inspeccion_tipo_respuesta_enum")
_ESTADO_ENUM = sa.Enum("BIEN", "OBSERVADO", name="item_inspeccion_estado_enum")
_XOR_CHECK = "ck_acta_inspeccion_item_xor_respuesta"


def upgrade() -> None:
    bind = op.get_bind()
    _TIPO_RESPUESTA_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "item_acta_inspeccion",
        sa.Column(
            "tipo_respuesta",
            _TIPO_RESPUESTA_ENUM,
            nullable=False,
            server_default="ESTADO",
        ),
    )

    op.alter_column(
        "acta_inspeccion_item",
        "estado",
        existing_type=_ESTADO_ENUM,
        nullable=True,
    )

    op.add_column(
        "acta_inspeccion_item",
        sa.Column("valor_si_no", sa.Boolean(), nullable=True),
    )

    op.create_check_constraint(
        _XOR_CHECK,
        "acta_inspeccion_item",
        "(estado IS NOT NULL AND valor_si_no IS NULL) OR (estado IS NULL AND valor_si_no IS NOT NULL)",
    )

    op.execute(
        sa.text(
            """
            INSERT INTO item_acta_inspeccion (codigo, nombre, activo, orden, tipo_respuesta)
            SELECT 'TIENE_HABILITACION', 'Tiene habilitación', TRUE, 6, 'SI_NO'
            WHERE NOT EXISTS (
                SELECT 1 FROM item_acta_inspeccion WHERE codigo = 'TIENE_HABILITACION'
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM acta_inspeccion_item
            WHERE item_acta_inspeccion_id IN (
                SELECT id FROM item_acta_inspeccion WHERE codigo = 'TIENE_HABILITACION'
            )
            """
        )
    )
    op.execute(
        sa.text("DELETE FROM item_acta_inspeccion WHERE codigo = 'TIENE_HABILITACION'")
    )

    op.drop_constraint(_XOR_CHECK, "acta_inspeccion_item", type_="check")
    op.drop_column("acta_inspeccion_item", "valor_si_no")

    op.alter_column(
        "acta_inspeccion_item",
        "estado",
        existing_type=_ESTADO_ENUM,
        nullable=False,
    )

    op.drop_column("item_acta_inspeccion", "tipo_respuesta")
    _TIPO_RESPUESTA_ENUM.drop(op.get_bind(), checkfirst=True)
