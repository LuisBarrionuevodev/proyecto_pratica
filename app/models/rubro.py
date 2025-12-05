from app.database import db


class Rubro(db.Model):
    __tablename__ = "rubro"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), nullable=False, unique=True, index=True)
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
    domicilio = db.relationship("Domicilio", back_populates="rubro")
    relevamiento = db.relationship("Relevamiento", back_populates="rubro")
