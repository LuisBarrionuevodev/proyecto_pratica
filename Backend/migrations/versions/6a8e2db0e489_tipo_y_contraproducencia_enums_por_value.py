"""tipo y contraproducencia enums por value

Revision ID: 6a8e2db0e489
Revises: ac50768d17fb
Create Date: 2026-01-02 05:13:26.365503
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a8e2db0e489"
down_revision = "ac50768d17fb"
branch_labels = None
depends_on = None


def upgrade():
    # --- TIPO (guardar values con espacios) ---
    op.execute(
        """
        ALTER TABLE actuaciones
        MODIFY COLUMN tipo ENUM(
            'INSPECCION',
            'REINSPECCION',
            'RATIFICACION DE CLAUSURA',
            'RATIFICACION DE DECOMISO',
            'VERIFICAR E INFORMAR',
            'TRANSPORTE'
        ) NULL;
        """
    )

    # --- CONTRAPRODUCENCIA (values humanos) ---
    op.execute(
        """
        ALTER TABLE actuaciones
        MODIFY COLUMN contraproducencia ENUM(
            'LOCAL CERRADO',
            'NO EXISTE/NO ES EL RUBRO',
            'CLIMA',
            'ZONA ROJA',
            'NO_HUBO',
            'OTROS'
        ) NULL;
        """
    )


def downgrade():
    # Si querés, podés volver a un VARCHAR(21) (o al tipo anterior que tenías)
    # O dejarlo como pass si no te interesa downgrade.
    op.execute(
        """
        ALTER TABLE actuaciones
        MODIFY COLUMN tipo VARCHAR(21) NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE actuaciones
        MODIFY COLUMN contraproducencia VARCHAR(21) NULL;
        """
    )

