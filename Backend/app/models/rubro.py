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

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "nombre": self.nombre,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_relations:
            dom = []
            if self.domicilio:
                for d in self.domicilio:
                    dom.append(d.to_dict())
            else:
                None
            data["domicilios"] = dom
        if include_relations:
            rele = []
            if self.relevamiento:
                for r in self.relevamiento:
                    rele.append(r.to_dict())
            else:
                None
            data["relevamientos"] = rele
        return data
