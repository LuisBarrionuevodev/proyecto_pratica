from app.database import db


class RutaTrabajo(db.Model):
    __tablename__ = "ruta_trabajo"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    turno = db.Column(
        db.Enum("MANIANA", "TARDE", name="tipo_turno"),
        nullable=False,
        index=True,
    )
    estado_ruta = db.Column(
        db.Enum(
            "BORRADOR",
            "PUBLICADA",
            "EN_CURSO",
            "CERRADA",
            "CANCELADA",
            name="estado_ruta_enum",
        ),
        nullable=False,
        default="BORRADOR",
        server_default="BORRADOR",
        index=True,
    )
    numero = db.Column(db.SmallInteger, nullable=False, default=1, server_default="1")
    observaciones = db.Column(db.Text, nullable=True)
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

    created_by_user = db.relationship("User")
    grupos = db.relationship("RutaGrupo", back_populates="ruta_trabajo")
    items = db.relationship("RutaItem", back_populates="ruta_trabajo")

    __table_args__ = (
        db.UniqueConstraint("fecha", "turno", "numero", name="uq_ruta_trabajo_fecha_turno_numero"),
        db.Index("ix_ruta_trabajo_fecha_turno_estado", "fecha", "turno", "estado_ruta"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "turno": self.turno,
            "estado_ruta": self.estado_ruta,
            "numero": self.numero,
            "observaciones": self.observaciones,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
