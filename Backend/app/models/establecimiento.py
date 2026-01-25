from app.database import db


class Establecimiento(db.Model):
    __tablename__ = "establecimientos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), nullable=False, unique=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
        }
