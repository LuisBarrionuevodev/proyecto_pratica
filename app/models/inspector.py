from app.database import db
from app.models import actuaciones_inspector


class Inspector(db.Model):
    __tablename__ = "inspector"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )
    legajo = db.Column(
        db.String(5),
        nullable=False,
        index=True,
    )
    turno_id = db.Column(
        db.Integer,
        db.ForeignKey("turno.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
    )

    actuaciones = db.relationship(
        "Actuaciones", secondary=actuaciones_inspector, back_populates="inspector"
    )
    turno = db.relationship("Turno", back_populates="inspector")
