from app.database import db


class RutaItem(db.Model):
    __tablename__ = "ruta_item"

    id = db.Column(db.Integer, primary_key=True)
    ruta_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_trabajo.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    ruta_grupo_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_grupo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    iniciador_ruta_id = db.Column(
        db.Integer,
        db.ForeignKey("iniciador_ruta.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    estado_ruta_item = db.Column(
        db.Enum(
            "PENDIENTE_ASIGNACION",
            "ASIGNADO",
            "EN_PROCESO",
            "FINALIZADO",
            "NO_REALIZADO",
            "CANCELADO",
            name="estado_ruta_item_enum",
        ),
        nullable=False,
        default="PENDIENTE_ASIGNACION",
        server_default="PENDIENTE_ASIGNACION",
        index=True,
    )
    estado_ejecucion = db.Column(
        db.Enum("REALIZADO", "NO_REALIZADO", name="estado_ejecucion_enum"),
        nullable=True,
        index=True,
    )
    motivo_no_realizado = db.Column(
        db.Enum(
            "LOCAL_CERRADO",
            "INCLEMENCIA_TIEMPO",
            "NO_EXISTE_LOCAL",
            "OTRO",
            name="motivo_no_realizado_enum",
        ),
        nullable=True,
        index=True,
    )
    observaciones_ejecucion = db.Column(db.Text, nullable=True)
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    ejecutado_por_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    ejecutado_at = db.Column(db.DateTime, nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    ruta_trabajo = db.relationship("RutaTrabajo", back_populates="items")
    ruta_grupo = db.relationship("RutaGrupo", back_populates="items")
    iniciador_ruta = db.relationship("IniciadorRuta", back_populates="ruta_items")
    actuacion = db.relationship("Actuaciones")
    ejecutado_por_user = db.relationship("User", foreign_keys=[ejecutado_por_user_id])
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])

    __table_args__ = (
        db.UniqueConstraint("ruta_trabajo_id", "iniciador_ruta_id", name="uq_ruta_item_ruta_iniciador"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ruta_trabajo_id": self.ruta_trabajo_id,
            "ruta_grupo_id": self.ruta_grupo_id,
            "iniciador_ruta_id": self.iniciador_ruta_id,
            "estado_ruta_item": self.estado_ruta_item,
            "estado_ejecucion": self.estado_ejecucion,
            "motivo_no_realizado": self.motivo_no_realizado,
            "observaciones_ejecucion": self.observaciones_ejecucion,
            "actuacion_id": self.actuacion_id,
            "ejecutado_por_user_id": self.ejecutado_por_user_id,
            "ejecutado_at": self.ejecutado_at.isoformat() if self.ejecutado_at else None,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
