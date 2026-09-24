from app.database import db


class LugarTrabajo(db.Model):
    __tablename__ = "lugares_trabajo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), nullable=False, index=True)  # no unique

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
        }
