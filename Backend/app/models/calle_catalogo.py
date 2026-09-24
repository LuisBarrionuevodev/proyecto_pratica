from app.database import db


class CalleCatalogo(db.Model):
    __tablename__ = "calle_catalogo"

    id = db.Column(db.Integer, primary_key=True)
    nombre_canonico = db.Column(db.String(255), nullable=False, unique=True)
    canon_base = db.Column(db.String(255), nullable=True, index=True)
    nombre_key = db.Column(db.String(255), nullable=False, unique=True, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
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
