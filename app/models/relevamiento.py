from sqlalchemy import event

from app.database import db


class Relevamiento(db.Model):
    __tablename__ = "relevamiento"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)

    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
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

    domicilio = db.relationship("Domicilio", back_populates="relevamiento")
    rubro = db.relationship("Rubro", back_populates="relevamiento")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "fecha": self.fecha,
            "anio": self.anio,
            "mes": self.mes,
            "domicilio_id": self.domicilio_id,
            "rubro_id": self.rubro_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            data["domicilio"] = self.domicilio.to_dict() if self.domicilio else None
            data["rubro"] = self.rubro.to_dict() if self.rubro else None
        return data



