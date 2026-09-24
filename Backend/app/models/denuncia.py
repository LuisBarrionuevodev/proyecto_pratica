from app.database import db


class Denuncia(db.Model):
    __tablename__ = "denuncia"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    motivo = db.Column(db.Text, nullable=False)
    estado = db.Column(
        db.Enum("ABIERTA", "CERRADA", "DESCARTADA", name="denuncia_estado_enum"),
        nullable=False,
        default="ABIERTA",
        server_default="ABIERTA",
        index=True,
    )
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
    deleted_at = db.Column(db.DateTime, nullable=True)

    domicilio = db.relationship("Domicilio")
    created_by_user = db.relationship("User")
    iniciadores_ruta = db.relationship("IniciadorRuta", back_populates="denuncia")

    __table_args__ = (
        db.Index("ix_denuncia_anio_mes_estado", "anio", "mes", "estado"),
        db.Index("ix_denuncia_anio_mes_domicilio_id", "anio", "mes", "domicilio_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "anio": self.anio,
            "mes": self.mes,
            "domicilio_id": self.domicilio_id,
            "motivo": self.motivo,
            "estado": self.estado,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
