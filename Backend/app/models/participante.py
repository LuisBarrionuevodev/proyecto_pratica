from app.database import db


class Participante(db.Model):
    __tablename__ = "participantes"

    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(128), nullable=False)
    apellido = db.Column(db.String(128), nullable=False)
    lugar_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("lugares_trabajo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    lugar_trabajo = db.relationship("LugarTrabajo")

    def to_dict(self):
        return {
            "id": self.id,
            "dni": self.dni,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "lugar_trabajo_id": self.lugar_trabajo_id,
        }
