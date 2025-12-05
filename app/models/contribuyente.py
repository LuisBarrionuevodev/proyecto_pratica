from app.database import db


class Contribuyente(db.Model):
    __tablename__ = "contribuyente"

    id = db.Column(db.Integer, primary_key=True)
    apellido = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )
    nombre = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )
    documento = db.Column(
        db.String(11),
        nullable=False,
        index=True,
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
    domicilio = db.relationship("Domicilio", back_populates="contribuyente")
