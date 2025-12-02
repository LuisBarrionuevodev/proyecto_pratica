from datetime import datetime

from app.database import db


class Notificacion(db.Model):
    __tablename__ = "notificacion"
    id = db.Column(db.Intege, primary_key=True)
    numero_acta = db.Column(db.String(6), nullable=False)
    anio = db.Column(db.Integer, default=lambda: datetime.now().year, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    actuaciones = db.relationship("actuaciones", back_populates="notificacion")
