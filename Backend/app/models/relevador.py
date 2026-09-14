from app.database import db


class Relevador(db.Model):
    __tablename__ = "relevador"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), nullable=False, unique=True, index=True)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text("TRUE"))
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

    relevamientos = db.relationship(
        "Relevamiento",
        secondary="relevamiento_relevador",
        back_populates="relevadores",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
        }
