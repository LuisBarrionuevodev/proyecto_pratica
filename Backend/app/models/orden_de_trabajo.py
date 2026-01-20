from sqlalchemy import event

from app.database import db


class OrdenTrabajo(db.Model):
    __tablename__ = "orden_trabajo"
    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )
    mes = db.Column(
        db.Integer,
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
    deleted_at = db.Column(
        db.DateTime,
        nullable=True,
    )
    actuaciones = db.relationship("Actuaciones", back_populates="orden_trabajo")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_ot_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_acta": self.numero_acta,
            "anio": self.anio,
            "mes": self.mes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }

        if include_relations:
            data["actuacion"] = self.actuaciones.to_dict() if self.actuaciones else None

        return data


