from app.database import db


class ItemActaInspeccion(db.Model):
    """Catálogo de condiciones verificables en acta de inspección."""

    __tablename__ = "item_acta_inspeccion"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(64), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(128), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, server_default=db.text("TRUE"))
    orden = db.Column(db.Integer, nullable=False, index=True)

    inspeccion_junctions = db.relationship(
        "ActaInspeccionItem",
        back_populates="item",
        lazy="select",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "activo": self.activo,
            "orden": self.orden,
        }
