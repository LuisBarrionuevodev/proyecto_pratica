from datetime import datetime

from app.database import db


class Oficio(db.Model):
    __tablename__ = "oficio"

    id = db.Column(db.Integer, primary_key=True)

    numero_oficio = db.Column(
        db.String(30),
        nullable=False,
        index=True,
    )
    anio = db.Column(
        db.Integer,
        default=lambda: datetime.now().year,
        nullable=False,
        index=True,
    )
    causa = db.Column(
        db.String(10),
        nullable=True,
        index=True,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
        nullable=True,
    )

    comprobacion = db.relationship("Comprobacion", back_populates="oficio")
    expediente = db.relationship("Expediente", back_populates="oficio")
    __table_args__ = (
        db.UniqueConstraint("numero_oficio", "anio", name="uq_of_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_oficio": self.numero_oficio,
            "anio": self.anio,
            "causa": self.causa,
            "comprobacion_id": self.comprobacion_id,
        }

        if include_relations:
            data["comprobacion"] = (
                self.comprobacion.to_dict() if self.comprobacion else None
            )

        if include_relations:
            data["expedientes"] = [e.to_dict() for e in self.expediente] if self.expediente else []


        return data
