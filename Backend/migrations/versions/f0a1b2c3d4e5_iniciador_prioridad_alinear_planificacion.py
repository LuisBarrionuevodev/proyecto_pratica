"""iniciador_ruta: alinear prioridad a escala Planificación (1=BAJA, 3+=ALTA).

Corrige datos generados con la policy anterior invertida respecto de
`planificacion_prioridad` (relevamiento quedaba en 3=ALTA; denuncia/reinspección en 1–2=BAJA/MEDIA).
"""

from alembic import op


revision = "f0a1b2c3d4e5"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Relevamiento: valor 3 era el antiguo "PRIORIDAD_BAJA" mal etiquetado → debe ser 1 (BAJA).
    op.execute(
        """
        UPDATE iniciador_ruta
        SET prioridad = 1
        WHERE tipo_iniciador = 'RELEVAMIENTO'
          AND prioridad IN (2, 3)
        """
    )
    # Denuncia: antigua "media" (2) → ALTA (3); cualquier valor <3 se normaliza a ALTA.
    op.execute(
        """
        UPDATE iniciador_ruta
        SET prioridad = 3
        WHERE tipo_iniciador = 'DENUNCIA'
          AND prioridad < 3
        """
    )
    # Reinspección notificación / oficios: antigua prioridad 1 (= errónea BAJA en UI) → ALTA.
    op.execute(
        """
        UPDATE iniciador_ruta
        SET prioridad = 3
        WHERE tipo_iniciador IN (
            'REINSPECCION_NOTIFICACION',
            'REINSPECCION_OFICIO',
            'VERIFICAR_INFORMAR_OFICIO',
            'RATIFICACION_CLAUSURA_OFICIO',
            'RATIFICACION_DECOMISO_OFICIO'
        )
          AND prioridad < 3
        """
    )


def downgrade() -> None:
    # No se revierte: la escala anterior era inconsistente con Planificación.
    pass
