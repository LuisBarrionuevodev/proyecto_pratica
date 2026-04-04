"""iniciador_ruta: índice único funcional para REINSPECCION_NOTIFICACION vencida (Fase B)

Evita más de un iniciador bloqueante (estados que materializan traza activa) por notificación
para tipo REINSPECCION_NOTIFICACION, sin impedir historial en estados terminales.

Implementación: `CREATE UNIQUE INDEX ... ON iniciador_ruta ((CASE ... END))` (MySQL 8.0.13+).
Se evita `ADD COLUMN ... GENERATED STORED`, que en algunos entornos InnoDB devolvía error 1215
("Cannot add foreign key constraint") al alterar tablas con muchas FKs.

Revision ID: b2c8e9f1a3d4
Revises: 3f4023e6e9fc
Create Date: 2026-03-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b2c8e9f1a3d4"
down_revision = "3f4023e6e9fc"
branch_labels = None
depends_on = None


# Estados que generan clave única (alineados a `inactive_estados()` inverso en notificacion_iniciador).
_ESTADOS_BLOQUEANTES_SQL = (
    "'PENDIENTE','PLANIFICADO','EN_EJECUCION','CUMPLIDO','NO_REALIZADO_REPROGRAMAR'"
)


def upgrade():
    conn = op.get_bind()

    dup = conn.execute(
        sa.text(
            f"""
            SELECT notificacion_id, COUNT(*) AS cnt
            FROM iniciador_ruta
            WHERE deleted_at IS NULL
              AND tipo_iniciador = 'REINSPECCION_NOTIFICACION'
              AND notificacion_id IS NOT NULL
              AND estado_iniciador IN ({_ESTADOS_BLOQUEANTES_SQL})
            GROUP BY notificacion_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if dup:
        ids = [row[0] for row in dup]
        raise RuntimeError(
            "Migración bloqueada: existen notificacion_id con más de un iniciador "
            "REINSPECCION_NOTIFICACION en estado bloqueante. Corregir datos antes de aplicar. "
            f"notificacion_id afectados (muestra): {ids[:20]}"
        )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_iniciador_ruta_reinsp_notif_vencida_key
        ON iniciador_ruta (
            (
                CASE
                    WHEN deleted_at IS NULL
                        AND tipo_iniciador = 'REINSPECCION_NOTIFICACION'
                        AND notificacion_id IS NOT NULL
                        AND estado_iniciador IN (
                            'PENDIENTE','PLANIFICADO','EN_EJECUCION','CUMPLIDO','NO_REALIZADO_REPROGRAMAR'
                        )
                    THEN CONCAT('REINSP_NOTIF_VENC:', notificacion_id)
                    ELSE NULL
                END
            )
        )
        """
    )


def downgrade():
    op.drop_index(
        "uq_iniciador_ruta_reinsp_notif_vencida_key",
        table_name="iniciador_ruta",
    )
