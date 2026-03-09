"""phase1 rutas iniciadores

Revision ID: 7a1c9e4d2b11
Revises: 589c4b79b2fa
Create Date: 2026-03-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a1c9e4d2b11"
down_revision = "589c4b79b2fa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "denuncia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("domicilio_id", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "ABIERTA",
                "CERRADA",
                "DESCARTADA",
                name="denuncia_estado_enum",
                native_enum=False,
            ),
            server_default="ABIERTA",
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["domicilio_id"], ["domicilio.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("denuncia", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_denuncia_fecha"), ["fecha"], unique=False)
        batch_op.create_index(batch_op.f("ix_denuncia_anio"), ["anio"], unique=False)
        batch_op.create_index(batch_op.f("ix_denuncia_mes"), ["mes"], unique=False)
        batch_op.create_index(batch_op.f("ix_denuncia_domicilio_id"), ["domicilio_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_denuncia_estado"), ["estado"], unique=False)
        batch_op.create_index(batch_op.f("ix_denuncia_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_index("ix_denuncia_anio_mes_estado", ["anio", "mes", "estado"], unique=False)
        batch_op.create_index("ix_denuncia_anio_mes_domicilio_id", ["anio", "mes", "domicilio_id"], unique=False)

    op.create_table(
        "iniciador_ruta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo_iniciador",
            sa.Enum(
                "RELEVAMIENTO",
                "DENUNCIA",
                "REINSPECCION_NOTIFICACION",
                "VERIFICAR_INFORMAR_OFICIO",
                "RATIFICACION_CLAUSURA_OFICIO",
                "RATIFICACION_DECOMISO_OFICIO",
                name="tipo_iniciador_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "estado_iniciador",
            sa.Enum(
                "PENDIENTE",
                "PLANIFICADO",
                "EN_EJECUCION",
                "CUMPLIDO",
                "NO_REALIZADO_REPROGRAMAR",
                "CERRADO",
                "CERRADO_NO_EXISTE_LOCAL",
                "ANULADO",
                name="estado_iniciador_enum",
                native_enum=False,
            ),
            server_default="PENDIENTE",
            nullable=False,
        ),
        sa.Column("fecha_origen", sa.Date(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("domicilio_id", sa.Integer(), nullable=False),
        sa.Column(
            "turno_sugerido",
            sa.Enum("TARDE", "MANIANA", name="tipo_turno", native_enum=False),
            nullable=True,
        ),
        sa.Column("prioridad", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("cerrado_at", sa.DateTime(), nullable=True),
        sa.Column("cerrado_motivo", sa.String(length=255), nullable=True),
        sa.Column("denuncia_id", sa.Integer(), nullable=True),
        sa.Column("relevamiento_id", sa.Integer(), nullable=True),
        sa.Column("notificacion_id", sa.Integer(), nullable=True),
        sa.Column("comprobacion_id", sa.Integer(), nullable=True),
        sa.Column("oficio_id", sa.Integer(), nullable=True),
        sa.Column("actuacion_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actuacion_id"], ["actuaciones.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["comprobacion_id"], ["comprobacion.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["denuncia_id"], ["denuncia.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["domicilio_id"], ["domicilio.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["notificacion_id"], ["notificacion.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["oficio_id"], ["oficio.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["relevamiento_id"], ["relevamiento.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("iniciador_ruta", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_tipo_iniciador"), ["tipo_iniciador"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_estado_iniciador"), ["estado_iniciador"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_fecha_origen"), ["fecha_origen"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_anio"), ["anio"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_mes"), ["mes"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_domicilio_id"), ["domicilio_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_turno_sugerido"), ["turno_sugerido"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_denuncia_id"), ["denuncia_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_relevamiento_id"), ["relevamiento_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_notificacion_id"), ["notificacion_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_comprobacion_id"), ["comprobacion_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_oficio_id"), ["oficio_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_actuacion_id"), ["actuacion_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_iniciador_ruta_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_index("ix_iniciador_ruta_anio_mes_estado", ["anio", "mes", "estado_iniciador"], unique=False)
        batch_op.create_index("ix_iniciador_ruta_anio_mes_tipo", ["anio", "mes", "tipo_iniciador"], unique=False)
        batch_op.create_index(
            "ix_iniciador_ruta_anio_mes_turno_estado",
            ["anio", "mes", "turno_sugerido", "estado_iniciador"],
            unique=False,
        )

    op.create_table(
        "ruta_trabajo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column(
            "turno",
            sa.Enum("TARDE", "MANIANA", name="tipo_turno", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "estado_ruta",
            sa.Enum(
                "BORRADOR",
                "PUBLICADA",
                "EN_CURSO",
                "CERRADA",
                "CANCELADA",
                name="estado_ruta_enum",
                native_enum=False,
            ),
            server_default="BORRADOR",
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fecha", "turno", "numero", name="uq_ruta_trabajo_fecha_turno_numero"),
    )
    with op.batch_alter_table("ruta_trabajo", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ruta_trabajo_fecha"), ["fecha"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_trabajo_turno"), ["turno"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_trabajo_estado_ruta"), ["estado_ruta"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_trabajo_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_index("ix_ruta_trabajo_fecha_turno_estado", ["fecha", "turno", "estado_ruta"], unique=False)

    op.create_table(
        "ruta_grupo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruta_trabajo_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ruta_trabajo_id"], ["ruta_trabajo.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ruta_trabajo_id", "nombre", name="uq_ruta_grupo_ruta_nombre"),
    )
    with op.batch_alter_table("ruta_grupo", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ruta_grupo_ruta_trabajo_id"), ["ruta_trabajo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_grupo_created_by_user_id"), ["created_by_user_id"], unique=False)

    op.create_table(
        "ruta_grupo_inspector",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruta_grupo_id", sa.Integer(), nullable=False),
        sa.Column("inspector_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inspector_id"], ["inspector.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ruta_grupo_id"], ["ruta_grupo.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ruta_grupo_id", "inspector_id", name="uq_ruta_grupo_inspector"),
    )
    with op.batch_alter_table("ruta_grupo_inspector", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ruta_grupo_inspector_ruta_grupo_id"), ["ruta_grupo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_grupo_inspector_inspector_id"), ["inspector_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_ruta_grupo_inspector_created_by_user_id"),
            ["created_by_user_id"],
            unique=False,
        )

    op.create_table(
        "ruta_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruta_trabajo_id", sa.Integer(), nullable=False),
        sa.Column("ruta_grupo_id", sa.Integer(), nullable=True),
        sa.Column("iniciador_ruta_id", sa.Integer(), nullable=False),
        sa.Column(
            "estado_ruta_item",
            sa.Enum(
                "PENDIENTE_ASIGNACION",
                "ASIGNADO",
                "EN_PROCESO",
                "FINALIZADO",
                "NO_REALIZADO",
                "CANCELADO",
                name="estado_ruta_item_enum",
                native_enum=False,
            ),
            server_default="PENDIENTE_ASIGNACION",
            nullable=False,
        ),
        sa.Column(
            "estado_ejecucion",
            sa.Enum("REALIZADO", "NO_REALIZADO", name="estado_ejecucion_enum", native_enum=False),
            nullable=True,
        ),
        sa.Column(
            "motivo_no_realizado",
            sa.Enum(
                "LOCAL_CERRADO",
                "INCLEMENCIA_TIEMPO",
                "NO_EXISTE_LOCAL",
                "OTRO",
                name="motivo_no_realizado_enum",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("observaciones_ejecucion", sa.Text(), nullable=True),
        sa.Column("actuacion_id", sa.Integer(), nullable=True),
        sa.Column("ejecutado_por_user_id", sa.Integer(), nullable=True),
        sa.Column("ejecutado_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actuacion_id"], ["actuaciones.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ejecutado_por_user_id"], ["users.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["iniciador_ruta_id"], ["iniciador_ruta.id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ruta_grupo_id"], ["ruta_grupo.id"], onupdate="CASCADE", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ruta_trabajo_id"], ["ruta_trabajo.id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ruta_trabajo_id", "iniciador_ruta_id", name="uq_ruta_item_ruta_iniciador"),
    )
    with op.batch_alter_table("ruta_item", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ruta_item_ruta_trabajo_id"), ["ruta_trabajo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_ruta_grupo_id"), ["ruta_grupo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_iniciador_ruta_id"), ["iniciador_ruta_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_estado_ruta_item"), ["estado_ruta_item"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_estado_ejecucion"), ["estado_ejecucion"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_motivo_no_realizado"), ["motivo_no_realizado"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_actuacion_id"), ["actuacion_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_ejecutado_por_user_id"), ["ejecutado_por_user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ruta_item_created_by_user_id"), ["created_by_user_id"], unique=False)

    with op.batch_alter_table("relevamiento", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "turno_carga",
                sa.Enum("TARDE", "MANIANA", name="tipo_turno", native_enum=False),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_relevamiento_turno_carga"), ["turno_carga"], unique=False)
        batch_op.create_index(batch_op.f("ix_relevamiento_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_relevamiento_created_by_user_id_users",
            "users",
            ["created_by_user_id"],
            ["id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("expediente", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tipo_expediente",
                sa.Enum(
                    "ENVIO_ACTA",
                    "RESPUESTA_OFICIO",
                    "PRORROGA_NOTIFICACION",
                    "OTRO",
                    name="tipo_expediente_enum",
                    native_enum=False,
                ),
                nullable=True,
            )
        )
        batch_op.create_index(batch_op.f("ix_expediente_tipo_expediente"), ["tipo_expediente"], unique=False)

    with op.batch_alter_table("oficio", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expediente_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_oficio_expediente_id"), ["expediente_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_oficio_expediente_id_expediente",
            "expediente",
            ["expediente_id"],
            ["id"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
        )


def downgrade():
    with op.batch_alter_table("oficio", schema=None) as batch_op:
        batch_op.drop_constraint("fk_oficio_expediente_id_expediente", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_oficio_expediente_id"))
        batch_op.drop_column("expediente_id")

    with op.batch_alter_table("expediente", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_expediente_tipo_expediente"))
        batch_op.drop_column("tipo_expediente")

    with op.batch_alter_table("relevamiento", schema=None) as batch_op:
        batch_op.drop_constraint("fk_relevamiento_created_by_user_id_users", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_relevamiento_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_relevamiento_turno_carga"))
        batch_op.drop_column("created_by_user_id")
        batch_op.drop_column("turno_carga")

    with op.batch_alter_table("ruta_item", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ruta_item_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_ejecutado_por_user_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_actuacion_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_motivo_no_realizado"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_estado_ejecucion"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_estado_ruta_item"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_iniciador_ruta_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_ruta_grupo_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_item_ruta_trabajo_id"))
    op.drop_table("ruta_item")

    with op.batch_alter_table("ruta_grupo_inspector", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ruta_grupo_inspector_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_grupo_inspector_inspector_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_grupo_inspector_ruta_grupo_id"))
    op.drop_table("ruta_grupo_inspector")

    with op.batch_alter_table("ruta_grupo", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ruta_grupo_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_grupo_ruta_trabajo_id"))
    op.drop_table("ruta_grupo")

    with op.batch_alter_table("ruta_trabajo", schema=None) as batch_op:
        batch_op.drop_index("ix_ruta_trabajo_fecha_turno_estado")
        batch_op.drop_index(batch_op.f("ix_ruta_trabajo_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_ruta_trabajo_estado_ruta"))
        batch_op.drop_index(batch_op.f("ix_ruta_trabajo_turno"))
        batch_op.drop_index(batch_op.f("ix_ruta_trabajo_fecha"))
    op.drop_table("ruta_trabajo")

    with op.batch_alter_table("iniciador_ruta", schema=None) as batch_op:
        batch_op.drop_index("ix_iniciador_ruta_anio_mes_turno_estado")
        batch_op.drop_index("ix_iniciador_ruta_anio_mes_tipo")
        batch_op.drop_index("ix_iniciador_ruta_anio_mes_estado")
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_actuacion_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_oficio_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_comprobacion_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_notificacion_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_relevamiento_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_denuncia_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_turno_sugerido"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_domicilio_id"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_mes"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_anio"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_fecha_origen"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_estado_iniciador"))
        batch_op.drop_index(batch_op.f("ix_iniciador_ruta_tipo_iniciador"))
    op.drop_table("iniciador_ruta")

    with op.batch_alter_table("denuncia", schema=None) as batch_op:
        batch_op.drop_index("ix_denuncia_anio_mes_domicilio_id")
        batch_op.drop_index("ix_denuncia_anio_mes_estado")
        batch_op.drop_index(batch_op.f("ix_denuncia_created_by_user_id"))
        batch_op.drop_index(batch_op.f("ix_denuncia_estado"))
        batch_op.drop_index(batch_op.f("ix_denuncia_domicilio_id"))
        batch_op.drop_index(batch_op.f("ix_denuncia_mes"))
        batch_op.drop_index(batch_op.f("ix_denuncia_anio"))
        batch_op.drop_index(batch_op.f("ix_denuncia_fecha"))
    op.drop_table("denuncia")
