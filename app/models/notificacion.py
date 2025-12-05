from datetime import datetime

from app.database import db


class Notificacion(db.Model):
    __tablename__ = "notificacion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(
        db.Integer, nullable=False, index=True, default=lambda: datetime.now().year
    )
    mes = db.Column(
        db.Integer, nullable=False, index=True, default=lambda: datetime.now().month
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
    actuacion = db.relationship("Actuaciones", back_populates="notificacion")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_an_numero_anio"),
        db.Index("idx_notificacion_mes", "mes"),
        db.Index("idx_notificacion_anio", "anio"),
    )

    def to_dict(self, include_relations=False, include_actuaciones=False):
        data = {
            "id": self.id,
            "numero_acta": self.numero_acta,
            "anio": self.anio,
            "mes": self.mes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_actuaciones:
            acts = []
            if self.actuaciones:
                for a in self.actuaciones:
                    acts.append(a.to_dict())
            data["actuaciones"] = acts

        return data
