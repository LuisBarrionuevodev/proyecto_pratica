from app.database import db


class Contribuyente(db.Model):
    __tablename__ = "contribuyente"

    id = db.Column(db.Integer, primary_key=True)
    apellido = db.Column(
        db.String(128),
        nullable=True,
        index=True,
    )
    nombre = db.Column(
        db.String(128),
        nullable=True,
        index=True,
    )
    razon_social = db.Column(
        db.String(255),
        nullable=True,
        index=True,
    )
    documento = db.Column(
        db.String(11),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    deleted_at = db.Column(db.DateTime, nullable=True)
    domicilio = db.relationship("Domicilio", back_populates="contribuyente")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "apellido": self.apellido,
            "nombre": self.nombre,
            "razon_social": self.razon_social,
            "documento": self.documento,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            domicilios = []
            if self.domicilio:
                for d in self.domicilio:
                    domicilios.append(d.to_dict())
            data["domicilios"] = domicilios

        return data
