from sqlalchemy import event

from app.database import db


class Decomiso(db.Model):
    __tablename__ = "decomiso"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    cantidad = db.Column(db.Numeric(12, 3), nullable=False)
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
    actuaciones = db.relationship("Actuaciones", back_populates="decomiso")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_ad_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_acta": self.numero_acta,
            "anio": self.anio,
            "mes": self.mes,
            "actuacion_id": self.actuacion_id,
            "cantidad": str(self.cantidad) if self.cantidad is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            data["actuacion"] = self.actuacion.to_dict() if self.actuacion else None

        return data

