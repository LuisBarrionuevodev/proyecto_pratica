from app.database import db


class Expediente(db.Model):
    __tablename__ = "expediente"
    id = db.Column(db.Integer, primary_key=True)
    numero_expediente = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    fecha_expediente = db.Column(db.Date, nullable=True, index=True)
    anio = db.Column(db.String(4), nullable=False, index=True)
    tipo_expediente = db.Column(
        db.Enum(
            "ENVIO_ACTA",
            "RESPUESTA_OFICIO",
            "PRORROGA_NOTIFICACION",
            "OTRO",
            name="tipo_expediente_enum",
        ),
        nullable=True,
        index=True,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    notificacion_id = db.Column(
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    oficio_id = db.Column(
        db.Integer,
        db.ForeignKey("oficio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    deleted_at = db.Column(db.DateTime, nullable=True)
    comprobacion = db.relationship("Comprobacion", back_populates="expediente")
    notificacion = db.relationship("Notificacion", back_populates="expedientes")
    oficio = db.relationship(
        "Oficio",
        back_populates="expediente",
        foreign_keys=[oficio_id],
    )
    __table_args__ = (
        db.UniqueConstraint("numero_expediente", "anio", name="uq_ex_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_expediente": self.numero_expediente,
            "fecha_expediente": self.fecha_expediente.isoformat() if self.fecha_expediente else None,
            "anio": self.anio,
            "tipo_expediente": self.tipo_expediente,
            "comprobacion_id": self.comprobacion_id,
            "notificacion_id": self.notificacion_id,
            "oficio_id": self.oficio_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }

        if include_relations:
            data["comprobacion"] = (
                self.comprobacion.to_dict() if self.comprobacion else None
            )
            data["notificacion"] = (
                self.notificacion.to_dict() if self.notificacion else None
            )
            data["oficio"] = self.oficio.to_dict() if self.oficio else None

        return data
