from datetime import datetime

from app.database import db


class Comprobacion(db.Model):
    __tablename__ = "comprobacion"
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
    motivo = db.Column(db.String(255), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    actuaciones = db.relationship("Actuaciones", back_populates="comprobacion")
    oficio = db.relationship("Oficio", back_populates="comprobacion")
    expediente = db.relationship("Expediente", back_populates="comprobacion")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_acomp_numero_anio"),
    )

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_acta": self.numero_acta,
            "anio": self.anio,
            "mes": self.mes,
            "motivo": self.motivo,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            data["actuacion"] = self.actuacion.to_dict() if self.actuacion else None

            oficios = []
            if self.oficio:
                for o in self.oficio:
                    oficios.append(o.to_dict())
            data["oficios"] = oficios

            expedientes = []
            if self.expediente:
                for e in self.expediente:
                    expedientes.append(e.to_dict())
            data["expedientes"] = expedientes

        return data
