from app.database import db
from app.models.notificacion_motivo import notificacion_motivo

class Motivo(db.Model):
    __tablename__ = "motivo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, index=True)

    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # ✅ plural + secondary como objeto Table
    notificaciones = db.relationship(
        "Notificacion",
        secondary=notificacion_motivo,
        back_populates="motivos",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
        }
