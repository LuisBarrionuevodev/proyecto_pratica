"""INSPECCIÓN-CHECKLIST.2 — estados BIEN/OBSERVADO + personas sin carnet en Notificación.

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-09-11

PRECHECK (documentado):
- acta_inspeccion_item: 58 filas en 24 actuaciones (QA CHECKLIST.1).
- inspeccion.cantidad_carnets_sanidad <> 0: 14 filas.
- V1 no permite inferir BIEN/OBSERVADO → se eliminan junctions V1 sin migrar estado.
- cantidad_carnets_sanidad NO se traslada a Notificacion.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "b1c2d3e4f5a6"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None

_ESTADO_ENUM = sa.Enum("BIEN", "OBSERVADO", name="item_inspeccion_estado_enum")

_CATALOG_NAMES = [
    ("TIENE_BANO", "Baño"),
    ("TIENE_SALON", "Salón"),
    ("TIENE_DEPOSITO", "Depósito"),
    ("TIENE_COCINA_MESA_TRABAJO", "Cocina / mesa de trabajo"),
]


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    # V1 junctions sin estado: limpieza explícita (no inferir BIEN/OBSERVADO).
    op.execute(sa.text("DELETE FROM acta_inspeccion_item"))

    if not _has_column("acta_inspeccion_item", "estado"):
        _ESTADO_ENUM.create(op.get_bind(), checkfirst=True)
        op.add_column(
            "acta_inspeccion_item",
            sa.Column("estado", _ESTADO_ENUM, nullable=False),
        )

    op.execute(
        sa.text(
            """
            INSERT INTO item_acta_inspeccion (codigo, nombre, activo, orden)
            SELECT 'VAJILLA_MANTEL', 'Vajilla / mantel', TRUE, 5
            WHERE NOT EXISTS (
                SELECT 1 FROM item_acta_inspeccion WHERE codigo = 'VAJILLA_MANTEL'
            )
            """
        )
    )

    for codigo, nombre in _CATALOG_NAMES:
        op.execute(
            sa.text(
                "UPDATE item_acta_inspeccion SET nombre = :nombre WHERE codigo = :codigo"
            ).bindparams(nombre=nombre, codigo=codigo)
        )

    if not _has_column("notificacion", "cantidad_personas_sin_carnet_sanidad"):
        op.add_column(
            "notificacion",
            sa.Column(
                "cantidad_personas_sin_carnet_sanidad",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if _has_column("inspeccion", "cantidad_carnets_sanidad"):
        op.drop_column("inspeccion", "cantidad_carnets_sanidad")


def downgrade() -> None:
    if not _has_column("inspeccion", "cantidad_carnets_sanidad"):
        op.add_column(
            "inspeccion",
            sa.Column(
                "cantidad_carnets_sanidad",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if _has_column("notificacion", "cantidad_personas_sin_carnet_sanidad"):
        op.drop_column("notificacion", "cantidad_personas_sin_carnet_sanidad")

    op.execute(
        sa.text("DELETE FROM item_acta_inspeccion WHERE codigo = 'VAJILLA_MANTEL'")
    )

    if _has_column("acta_inspeccion_item", "estado"):
        op.drop_column("acta_inspeccion_item", "estado")
        _ESTADO_ENUM.drop(op.get_bind(), checkfirst=True)

    op.execute(sa.text("DELETE FROM acta_inspeccion_item"))
