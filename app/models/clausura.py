from datetime import datetime

from app.database import db


class Clausura(db.Model):
    __tablename__ = "clausura"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(db.String(6), nullable=False)
    anio = db.Column(db.Integer, default=lambda: datetime.now().year, nullable=False)
    actuacion_id = db.Column(
        db.Integer,
        db.Foreignkey("actuaciones.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    actuacion = db.relationship("actuaciones", back_populates="clausura")
