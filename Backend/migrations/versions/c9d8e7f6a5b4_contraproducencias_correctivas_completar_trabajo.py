"""contraproducencias correctivas completar trabajo (placeholder — ya aplicada en BD).

Revision ID: c9d8e7f6a5b4
Revises: 05a3b9d35a32
Create Date: 2026-05-01

"""
from __future__ import annotations

revision = "c9d8e7f6a5b4"
down_revision = "05a3b9d35a32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op: la revisión ya está aplicada en entornos existentes."""
    pass


def downgrade() -> None:
    pass
