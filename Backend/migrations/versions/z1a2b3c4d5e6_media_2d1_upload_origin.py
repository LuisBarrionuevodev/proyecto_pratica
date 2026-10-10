"""MEDIA.2D.1 — origen de carga en ruta_item_archivo.

Backfill de filas existentes (solo ``ruta_item_archivo``; ``archivo`` no tiene origen):

1. ``ADD COLUMN upload_origin … DEFAULT 'COMPLETAR_TRABAJO'`` — MySQL rellena todas las filas
   ya vinculadas (links con ``archivo`` PENDING o READY).
2. ``UPDATE ruta_item_archivo SET upload_origin = 'COMPLETAR_TRABAJO' WHERE upload_origin IS NULL``
   — idempotente por si quedara NULL.
3. ``ALTER COLUMN upload_origin … NOT NULL DEFAULT 'COMPLETAR_TRABAJO'`` — endurece el esquema (2D.1A).

Política: no hay señal histórica para distinguir Mis trabajos; todo lo preexistente se trata como
evidencia de cierre (``COMPLETAR_TRABAJO``). El listado de Completar trabajos sigue gobernado por
``evidencias_pendientes_abiertas``, no solo por este campo.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "z1a2b3c4d5e6"
down_revision = "y0z1a2b3c4d5"
branch_labels = None
depends_on = None

_UPLOAD_ORIGIN = sa.Enum(
    "COMPLETAR_TRABAJO",
    "MIS_TRABAJOS",
    name="ruta_item_archivo_upload_origin_enum",
)


def upgrade() -> None:
    _UPLOAD_ORIGIN.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "ruta_item_archivo",
        sa.Column(
            "upload_origin",
            _UPLOAD_ORIGIN,
            nullable=True,
            server_default="COMPLETAR_TRABAJO",
        ),
    )
    # Equivalente explícito al backfill del DEFAULT en filas ya existentes.
    op.execute(
        sa.text(
            "UPDATE ruta_item_archivo "
            "SET upload_origin = 'COMPLETAR_TRABAJO' "
            "WHERE upload_origin IS NULL"
        )
    )
    op.alter_column(
        "ruta_item_archivo",
        "upload_origin",
        existing_type=_UPLOAD_ORIGIN,
        type_=_UPLOAD_ORIGIN,
        nullable=False,
        server_default="COMPLETAR_TRABAJO",
        existing_nullable=True,
        existing_server_default="COMPLETAR_TRABAJO",
    )


def downgrade() -> None:
    op.drop_column("ruta_item_archivo", "upload_origin")
    _UPLOAD_ORIGIN.drop(op.get_bind(), checkfirst=True)
