import enum

from sqlalchemy import Enum

from app.database import db


class TipoTurno(enum.Enum):
    TARDE = "Tarde"
    MANIANA = "Mañana"


class Turno(db.Model):
    __tablename__ = "turno"
    id = db.Column(db.Integer, primary_key=True)
    turno = db.Column(
        Enum(TipoTurno, name="tipo_turno", native_enum=False),
        nullable=True,
        default=TipoTurno.MANIANA,
        index=True,
    )

    inspector = db.relationship("Inspector", back_populates="turno")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "turno": self.turno,
        }
        if include_relations:
            insp = []
            if self.inspector:
                for i in self.inspector:
                    insp.append(i.to_dict())
                data["inspectores"] = insp
            else:
                None
