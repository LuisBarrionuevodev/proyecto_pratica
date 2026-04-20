"""Purgar inspectores placeholder 0001–0020 (idempotente).

Si ``b7c8_seed_inspectores`` ya se había aplicado sin el bloque de borrado,
esta revisión completa el reemplazo. Repetir es seguro (0 filas afectadas).

Revision ID: c9d0_insp_legacy (nombre corto por límite de alembic_version en MySQL)

Revises: b7c8_seed_inspectores
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa

revision = "c9d0_insp_legacy"
down_revision = "b7c8_seed_inspectores"
branch_labels = None
depends_on = None

_LEGACY_LEGAJOS_SQL = ", ".join(f"'{i:04d}'" for i in range(1, 21))


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            f"DELETE FROM ruta_grupo_inspector WHERE inspector_id IN "
            f"(SELECT id FROM inspector WHERE legajo IN ({_LEGACY_LEGAJOS_SQL}))"
        )
    )
    conn.execute(
        sa.text(
            f"UPDATE relevamiento SET inspector_id = NULL WHERE inspector_id IN "
            f"(SELECT id FROM inspector WHERE legajo IN ({_LEGACY_LEGAJOS_SQL}))"
        )
    )
    conn.execute(sa.text(f"DELETE FROM inspector WHERE legajo IN ({_LEGACY_LEGAJOS_SQL})"))


def downgrade():
    pass
