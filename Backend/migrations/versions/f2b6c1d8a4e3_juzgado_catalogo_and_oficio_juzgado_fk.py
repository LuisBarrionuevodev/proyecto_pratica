"""add juzgado catalog and oficio.juzgado_id

Revision ID: f2b6c1d8a4e3
Revises: e1a7d0c9f4b2
Create Date: 2026-03-10 18:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2b6c1d8a4e3"
down_revision = "e1a7d0c9f4b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "juzgado_catalogo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=32), nullable=False),
        sa.Column("nombre", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("codigo", name="uq_juzgado_catalogo_codigo"),
        sa.UniqueConstraint("nombre", name="uq_juzgado_catalogo_nombre"),
    )
    op.create_index("ix_juzgado_catalogo_codigo", "juzgado_catalogo", ["codigo"], unique=True)
    op.create_index("ix_juzgado_catalogo_nombre", "juzgado_catalogo", ["nombre"], unique=True)

    juzgado_catalogo = sa.table(
        "juzgado_catalogo",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
    )
    op.bulk_insert(
        juzgado_catalogo,
        [
            {"codigo": "JUZGADO_I", "nombre": "Juzgado I"},
            {"codigo": "JUZGADO_II", "nombre": "Juzgado II"},
            {"codigo": "JUZGADO_III", "nombre": "Juzgado III"},
            {"codigo": "JUZGADO_IV", "nombre": "Juzgado IV"},
            {"codigo": "JUZGADO_V", "nombre": "Juzgado V"},
            {"codigo": "JUZGADO_VI", "nombre": "Juzgado VI"},
            {"codigo": "JUZGADO_VII", "nombre": "Juzgado VII"},
            {"codigo": "JUZGADO_VIII", "nombre": "Juzgado VIII"},
            {"codigo": "JUZGADO_IX", "nombre": "Juzgado IX"},
            {"codigo": "JUZGADO_X", "nombre": "Juzgado X"},
            {"codigo": "JUZGADO_XI", "nombre": "Juzgado XI"},
            {"codigo": "JUZGADO_XII", "nombre": "Juzgado XII"},
            {"codigo": "JUZGADO_XIII", "nombre": "Juzgado XIII"},
            {"codigo": "JUZGADO_XIV", "nombre": "Juzgado XIV"},
            {"codigo": "JUZGADO_XV", "nombre": "Juzgado XV"},
            {"codigo": "JUZGADO_XVI", "nombre": "Juzgado XVI"},
            {"codigo": "JUZGADO_XVII", "nombre": "Juzgado XVII"},
            {"codigo": "JUZGADO_XVIII", "nombre": "Juzgado XVIII"},
            {"codigo": "JUZGADO_XIX", "nombre": "Juzgado XIX"},
            {"codigo": "JUZGADO_XX", "nombre": "Juzgado XX"},
        ],
    )

    op.add_column("oficio", sa.Column("juzgado_id", sa.Integer(), nullable=True))
    op.create_index("ix_oficio_juzgado_id", "oficio", ["juzgado_id"], unique=False)
    op.create_foreign_key(
        "fk_oficio_juzgado_id",
        "oficio",
        "juzgado_catalogo",
        ["juzgado_id"],
        ["id"],
        ondelete="RESTRICT",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_oficio_juzgado_id", "oficio", type_="foreignkey")
    op.drop_index("ix_oficio_juzgado_id", table_name="oficio")
    op.drop_column("oficio", "juzgado_id")

    op.drop_index("ix_juzgado_catalogo_nombre", table_name="juzgado_catalogo")
    op.drop_index("ix_juzgado_catalogo_codigo", table_name="juzgado_catalogo")
    op.drop_table("juzgado_catalogo")
