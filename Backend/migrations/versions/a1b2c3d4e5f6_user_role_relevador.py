"""HOTFIX-CIERRE-DIA: rol RELEVADOR en users.role enum.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "mysql":
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('admin', 'usuario', 'relevador') NOT NULL DEFAULT 'usuario'"
        )
    else:
        # SQLite / otros: el enum es CHECK implícito en SQLAlchemy; sin ALTER de enum.
        pass


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "mysql":
        op.execute(
            "UPDATE users SET role = 'usuario' WHERE role = 'relevador'"
        )
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('admin', 'usuario') NOT NULL DEFAULT 'usuario'"
        )
