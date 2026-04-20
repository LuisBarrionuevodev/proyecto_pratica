"""Seed idempotente: inspectores Bromatología (nómina por afiliado/legajo).

Reemplaza los inspectores placeholder (legajo 0001–0020) por la nómina canónica:
primero inserta/actualiza por afiliado, luego libera FKs y borra esos legajos legacy.

Revision ID: b7c8_seed_inspectores
Revises: 2fa39231af89
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa

from app.domains.grid.seeds.inspectores_canonicos import INSPECTORES_CANONICO

revision = "b7c8_seed_inspectores"
down_revision = "2fa39231af89"
branch_labels = None
depends_on = None

# Legajos del seed demo anterior (run.py); mismo criterio que LEGACY_PLACEHOLDER_LEGAJOS.
_LEGACY_LEGAJOS_SQL = ", ".join(f"'{i:04d}'" for i in range(1, 21))


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO turno (id, turno) SELECT 1, 'MANIANA' "
            "WHERE NOT EXISTS (SELECT 1 FROM turno WHERE id = 1)"
        )
    )
    conn.execute(
        sa.text(
            "INSERT INTO turno (id, turno) SELECT 2, 'TARDE' "
            "WHERE NOT EXISTS (SELECT 1 FROM turno WHERE id = 2)"
        )
    )
    for nombre, legajo, turno_id in INSPECTORES_CANONICO:
        nombre_clean = nombre.strip()
        legajo_norm = legajo.strip()
        if legajo_norm.isdigit() and len(legajo_norm) < 5:
            legajo_norm = legajo_norm.zfill(5)
        row = conn.execute(
            sa.text("SELECT id FROM inspector WHERE legajo = :l"),
            {"l": legajo_norm},
        ).fetchone()
        if row:
            conn.execute(
                sa.text("UPDATE inspector SET nombre = :n, turno_id = :t WHERE legajo = :l"),
                {"n": nombre_clean, "t": turno_id, "l": legajo_norm},
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO inspector (nombre, legajo, turno_id) VALUES (:n, :l, :t)"
                ),
                {"n": nombre_clean, "t": turno_id, "l": legajo_norm},
            )

    # Sustituir placeholders: quitar asignaciones a grupos de ruta y relevamientos,
    # luego borrar filas inspector con legajo 0001–0020. Las filas en
    # actuaciones_inspector para esos ids se eliminan por ON DELETE CASCADE al inspector.
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
    conn.execute(
        sa.text(
            f"DELETE FROM inspector WHERE legajo IN ({_LEGACY_LEGAJOS_SQL})"
        )
    )


def downgrade():
    # No se revierte: no se pueden restaurar los placeholders sin datos perdidos.
    pass
