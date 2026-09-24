from app.database import db


class Evento(db.Model):
    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, index=True)
    establecimiento_id = db.Column(
        db.Integer,
        db.ForeignKey("establecimientos.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    establecimiento = db.relationship("Establecimiento")

    def to_dict(self):
        return {
            "id": self.id,
            "fecha": self.fecha,
            "establecimiento_id": self.establecimiento_id,
        }
