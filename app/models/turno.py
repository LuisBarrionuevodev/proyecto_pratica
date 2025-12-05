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


db.relationship("Inspector", back_populates="turno")
