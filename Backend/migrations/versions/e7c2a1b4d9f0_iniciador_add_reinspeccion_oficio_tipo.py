"""add REINSPECCION_OFICIO to tipo_iniciador_enum

Revision ID: e7c2a1b4d9f0
Revises: d5a4b9c1e2f3
Create Date: 2026-03-11 16:10:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "e7c2a1b4d9f0"
down_revision = "d5a4b9c1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE iniciador_ruta
        MODIFY COLUMN tipo_iniciador
        ENUM(
            'RELEVAMIENTO',
            'DENUNCIA',
            'REINSPECCION_OFICIO',
            'REINSPECCION_NOTIFICACION',
            'VERIFICAR_INFORMAR_OFICIO',
            'RATIFICACION_CLAUSURA_OFICIO',
            'RATIFICACION_DECOMISO_OFICIO'
        ) NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE iniciador_ruta
        MODIFY COLUMN tipo_iniciador
        ENUM(
            'RELEVAMIENTO',
            'DENUNCIA',
            'REINSPECCION_NOTIFICACION',
            'VERIFICAR_INFORMAR_OFICIO',
            'RATIFICACION_CLAUSURA_OFICIO',
            'RATIFICACION_DECOMISO_OFICIO'
        ) NOT NULL
        """
    )

