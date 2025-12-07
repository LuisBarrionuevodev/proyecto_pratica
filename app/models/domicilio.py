from app.database import db


class Domicilio(db.Model):
    __tablename__ = "domicilio"
    id = db.Column(db.Integer, primary_key=True)

    calle = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )
    numero = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )
    cp = db.Column(db.String(10), nullable=True, default="4000")
    barrio_id = db.Column(
        db.Integer,
        db.ForeignKey("barrio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    contribuyente_id = db.Column(
        db.Integer,
        db.ForeignKey("contribuyente.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
    )
    lat = db.Column(db.Numeric(9, 6), nullable=True)
    long = db.Column(db.Numeric(9, 6), nullable=True)
    created_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        nullable=False,
    )
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
        nullable=False,
    )
    rubro = db.relationship("Rubro", back_populates="domicilio")
    actuaciones = db.relationship("Actuaciones", back_populates="domicilio")
    barrio = db.relationship("Barrio", back_populates="domicilio")
    contribuyente = db.relationship("Contribuyente", back_populates="domicilio")
    relevamiento = db.relationship("Relevamiento", back_populates="domicilio")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "calle": self.calle,
            "numero": self.numero,
            "cp": self.cp,
            "barrio_id": self.barrio_id,
            "contribuyente_id": self.contribuyente_id,
            "rubro_id": self.rubro_id,
            "lat": str(self.lat) if self.lat is not None else None,
            "long": str(self.long) if self.long is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        if include_relations:
            data["barrio"] = self.barrio.to_dict() if self.barrio else None
            data["contribuyente"] = (
                self.contribuyente.to_dict() if self.contribuyente else None
            )
            data["rubro"] = self.rubro.to_dict() if self.rubro else None

            relevs = []
            if self.relevamiento:
                for r in self.relevamiento:
                    relevs.append(r.to_dict())
            data["relevamientos"] = relevs

            acts = []
            if self.actuaciones:
                for a in self.actuaciones:
                    acts.append(a.to_dict())
            data["actuaciones"] = acts

        return data
