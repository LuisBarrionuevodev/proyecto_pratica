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
    fecha_oficio = db.Column(
        db.Date,
        nullable=True,
        index=True,
    )
    causa = db.Column(
        db.String(255),
        nullable=True,
        index=True,
    )
    deleted_at = db.Column(db.DateTime, nullable=True)
    juzgado_id = db.Column(
        db.Integer,
        db.ForeignKey("juzgado_catalogo.id", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
        nullable=True,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
        nullable=True,
    )

    juzgado = db.relationship("JuzgadoCatalogo", back_populates="oficios")
    comprobacion = db.relationship("Comprobacion", back_populates="oficio")
    expediente = db.relationship(
        "Expediente",
        back_populates="oficio",
        foreign_keys="Expediente.oficio_id",
    )
    __table_args__ = (
        db.UniqueConstraint("numero_oficio", "anio", name="uq_of_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_oficio": self.numero_oficio,
            "anio": self.anio,
            "fecha_oficio": self.fecha_oficio.isoformat() if self.fecha_oficio else None,
            "causa": self.causa,
            "juzgado_id": self.juzgado_id,
            "comprobacion_id": self.comprobacion_id,
            "deleted_at": self.deleted_at,
        }

        if include_relations:
            data["juzgado"] = self.juzgado.to_dict() if self.juzgado else None
            data["comprobacion"] = (
                self.comprobacion.to_dict() if self.comprobacion else None
            )

        if include_relations:
            data["expedientes"] = [e.to_dict() for e in self.expediente] if self.expediente else []


        return data
