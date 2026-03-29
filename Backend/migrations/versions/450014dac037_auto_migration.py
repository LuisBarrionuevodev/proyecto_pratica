"""auto migration (geom nullable — omitido en MySQL)

Revision ID: 450014dac037
Revises: a00ee416407f
Create Date: 2026-03-19 00:21:03.929487

La autogeneración pedía `geom` nullable en `barrio`/`distrito`. En MySQL un índice
SPATIAL exige columna NOT NULL (error 1252), por lo que el ALTER no es aplicable
tal cual. Se deja la revisión como no-op para mantener la cadena de migraciones.
"""

revision = "450014dac037"
down_revision = "a00ee416407f"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
