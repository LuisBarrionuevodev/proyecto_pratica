"""V1.1-MEDIA.0A: categorías FOTO_ACTA, FOTO_DOCUMENTACION_LOCAL, FOTO_INSPECCION.

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-10-04
"""

from __future__ import annotations

from alembic import op

revision = "t0u1v2w3x4y5"
down_revision = "s9t0u1v2w3x4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN categoria ENUM(
            'ACTA_DOCUMENTACION',
            'FOTO_INSPECCION',
            'FOTO_ACTA',
            'FOTO_DOCUMENTACION_LOCAL'
        ) NOT NULL
        """
    )
    op.execute(
        """
        UPDATE ruta_item_archivo
        SET categoria = 'FOTO_ACTA'
        WHERE categoria = 'ACTA_DOCUMENTACION'
        """
    )
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN categoria ENUM(
            'FOTO_ACTA',
            'FOTO_DOCUMENTACION_LOCAL',
            'FOTO_INSPECCION'
        ) NOT NULL
        """
    )

    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN tipo_documento ENUM(
            'ACTA_INSPECCION',
            'ACTA_NOTIFICACION',
            'OTRO_DOCUMENTO',
            'OTRO_ACTA',
            'HABILITACION',
            'CARNET_MANIPULADOR',
            'CERTIFICADO_DESINFECCION',
            'OTRO_DOCUMENTO_LOCAL'
        ) NULL
        """
    )
    op.execute(
        """
        UPDATE ruta_item_archivo
        SET tipo_documento = 'OTRO_DOCUMENTO_LOCAL'
        WHERE tipo_documento = 'OTRO_DOCUMENTO'
        """
    )
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN tipo_documento ENUM(
            'ACTA_INSPECCION',
            'ACTA_NOTIFICACION',
            'OTRO_ACTA',
            'HABILITACION',
            'CARNET_MANIPULADOR',
            'CERTIFICADO_DESINFECCION',
            'OTRO_DOCUMENTO_LOCAL'
        ) NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN categoria ENUM(
            'ACTA_DOCUMENTACION',
            'FOTO_INSPECCION',
            'FOTO_ACTA',
            'FOTO_DOCUMENTACION_LOCAL'
        ) NOT NULL
        """
    )
    op.execute(
        """
        UPDATE ruta_item_archivo
        SET categoria = 'ACTA_DOCUMENTACION'
        WHERE categoria IN ('FOTO_ACTA', 'FOTO_DOCUMENTACION_LOCAL')
        """
    )
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN categoria ENUM(
            'ACTA_DOCUMENTACION',
            'FOTO_INSPECCION'
        ) NOT NULL
        """
    )

    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN tipo_documento ENUM(
            'ACTA_INSPECCION',
            'ACTA_NOTIFICACION',
            'OTRO_DOCUMENTO',
            'OTRO_ACTA',
            'HABILITACION',
            'CARNET_MANIPULADOR',
            'CERTIFICADO_DESINFECCION',
            'OTRO_DOCUMENTO_LOCAL'
        ) NULL
        """
    )
    op.execute(
        """
        UPDATE ruta_item_archivo
        SET tipo_documento = 'OTRO_DOCUMENTO'
        WHERE tipo_documento IN ('OTRO_ACTA', 'OTRO_DOCUMENTO_LOCAL')
        """
    )
    op.execute(
        """
        ALTER TABLE ruta_item_archivo
        MODIFY COLUMN tipo_documento ENUM(
            'ACTA_INSPECCION',
            'ACTA_NOTIFICACION',
            'OTRO_DOCUMENTO'
        ) NULL
        """
    )
