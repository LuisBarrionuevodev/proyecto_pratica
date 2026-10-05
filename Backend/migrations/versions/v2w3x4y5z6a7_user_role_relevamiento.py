"""V1.1-RELEVAMIENTO-ROLE.1: rol relevamiento (carga/gestión) en users.role enum.

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-10-04
"""

from __future__ import annotations

from alembic import op

revision = "v2w3x4y5z6a7"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('admin', 'usuario', 'relevador', 'relevamiento') NOT NULL DEFAULT 'usuario'"
        )
    else:
        # SQLite / otros: enum lógico en SQLAlchemy; sin ALTER de enum nativo.
        pass


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "mysql":
        op.execute("UPDATE users SET role = 'usuario' WHERE role = 'relevamiento'")
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('admin', 'usuario', 'relevador') NOT NULL DEFAULT 'usuario'"
        )
