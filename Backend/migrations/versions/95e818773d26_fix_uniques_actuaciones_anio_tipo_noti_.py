"""fix uniques actuaciones anio+tipo+noti/compro

Revision ID: 95e818773d26
Revises: ac902f362388
Create Date: 2026-01-06 16:30:39.734690

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95e818773d26'
down_revision = 'ac902f362388'
branch_labels = None
depends_on = None


def upgrade():
    # Por si quedaron índices con nombres “raros”, estos drops son opcionales.
    # Si ya los dropeaste por SQL, podés comentar esto.
    try:
        op.drop_constraint("uq_act_anio_tipo_notificacion", "actuaciones", type_="unique")
    except Exception:
        pass

    try:
        op.drop_constraint("uq_act_anio_tipo_comprobacion", "actuaciones", type_="unique")
    except Exception:
        pass

    # ✅ Crear uniques correctos
    op.create_unique_constraint(
        "uq_act_anio_tipo_notificacion",
        "actuaciones",
        ["anio", "tipo", "notificacion_id"],
    )

    op.create_unique_constraint(
        "uq_act_anio_tipo_comprobacion",
        "actuaciones",
        ["anio", "tipo", "comprobacion_id"],
    )


def downgrade():
    op.drop_constraint("uq_act_anio_tipo_notificacion", "actuaciones", type_="unique")
    op.drop_constraint("uq_act_anio_tipo_comprobacion", "actuaciones", type_="unique")