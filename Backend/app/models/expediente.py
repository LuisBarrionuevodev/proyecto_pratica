from app.database import db


class Expediente(db.Model):
    __tablename__ = "expediente"
    id = db.Column(db.Integer, primary_key=True)
    numero_expediente = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.String(4), nullable=False, index=True)
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
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
    comprobacion = db.relationship("Comprobacion", back_populates="expediente")
    oficio = db.relationship("Oficio", back_populates="expediente")
    __table_args__ = (
        db.UniqueConstraint("numero_expediente", "anio", name="uq_ex_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_expediente": self.numero_expediente,
            "anio": self.anio,
            "comprobacion_id": self.comprobacion_id,
            "oficio_id": self.oficio_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            data["comprobacion"] = (
                self.comprobacion.to_dict() if self.comprobacion else None
            )
            data["oficio"] = self.oficio.to_dict() if self.oficio else None

        return data
