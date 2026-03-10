from app.database import db


class JuzgadoCatalogo(db.Model):
    __tablename__ = "juzgado_catalogo"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(32), nullable=False, unique=True, index=True)
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

    oficios = db.relationship("Oficio", back_populates="juzgado")

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
        }
