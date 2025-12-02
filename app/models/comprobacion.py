from datetime import datetime

from app.database import db


class Comprobacion(db.Model):
    __tablename__ = "acta_comprobacion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(db.String(6), nullable=False)
    anio = db.Column(db.Integer, default=lambda: datetime.now().year, nullable=False)
    motivo = db.Column(db.Text, nulleable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    actuacion = db.relationship("actuaciones", back_populate="acta_comprobacion")
