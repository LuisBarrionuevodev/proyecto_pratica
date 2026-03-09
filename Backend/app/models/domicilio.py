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
        db.String(200),
        nullable=False,
        index=True,
    )
    numero_tipo = db.Column(db.String(16), nullable=True, index=True)
    cp = db.Column(db.String(4), nullable=True, default="4000")
    ciudad = db.Column(db.String(110), nullable=True, default="San Miguel de Tucuman")
    provincia = db.Column(db.String(8), nullable=True, default="Tucuman")
    pais = db.Column(db.String(25), nullable=True, default="Argentina")
    barrio_id = db.Column(
        db.Integer,
        db.ForeignKey("barrio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    distrito_id = db.Column(
        db.Integer,
        db.ForeignKey("distrito.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    contribuyente_id = db.Column(
        db.Integer,
        db.ForeignKey("contribuyente.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,  # permite domicilio sin contribuyente (contraproducencia)
        unique=False,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,  # permite domicilio sin rubro (contraproducencia)
        unique=False,
        index=True,
    )
    calle_raw = db.Column(db.String(128), nullable=True)
    calle_normalizada = db.Column(db.String(128), nullable=True)
    calle_key = db.Column(db.String(128), nullable=True, index=True)
    calle_catalogo_id = db.Column(
        db.Integer,
        db.ForeignKey("calle_catalogo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    calle_norm_status = db.Column(
        db.String(32),
        nullable=False,
        default="PENDIENTE",
        index=True,
    )
    calle_norm_score = db.Column(db.Float, nullable=True)
    calle_norm_error = db.Column(db.String(255), nullable=True)
    calle_norm_updated_at = db.Column(db.DateTime, nullable=True)
    esquina_raw = db.Column(db.String(255), nullable=True)
    esquina_catalogo_id = db.Column(
        db.Integer,
        db.ForeignKey("calle_catalogo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    esquina_normalizada = db.Column(db.String(255), nullable=True)
    esquina_norm_status = db.Column(db.String(16), nullable=True, index=True)
    esquina_norm_score = db.Column(db.Float, nullable=True)
    esquina_norm_error = db.Column(db.String(255), nullable=True)
    esquina_norm_updated_at = db.Column(db.DateTime, nullable=True)
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
    deleted_at = db.Column(db.DateTime, nullable=True)
    rubro = db.relationship("Rubro", back_populates="domicilio")
    calle_catalogo = db.relationship(
        "CalleCatalogo",
        foreign_keys=[calle_catalogo_id],
    )
    esquina_catalogo = db.relationship(
        "CalleCatalogo",
        foreign_keys=[esquina_catalogo_id],
    )
    geocode = db.relationship("DomicilioGeocode", uselist=False, back_populates="domicilio")
    actuaciones = db.relationship("Actuaciones", back_populates="domicilio")
    barrio = db.relationship("Barrio", back_populates="domicilio")
    distrito = db.relationship("Distrito", back_populates="domicilio")
    contribuyente = db.relationship("Contribuyente", back_populates="domicilio")
    relevamiento = db.relationship("Relevamiento", back_populates="domicilio")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "calle": self.calle,
            "numero": self.numero,
            "numero_tipo": self.numero_tipo,
            "cp": self.cp,
            "barrio_id": self.barrio_id,
            "contribuyente_id": self.contribuyente_id,
            "rubro_id": self.rubro_id,
            "lat": str(self.lat) if self.lat is not None else None,
            "long": str(self.long) if self.long is not None else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "esquina_raw": self.esquina_raw,
            "esquina_normalizada": self.esquina_normalizada,
            "esquina_status": self.esquina_norm_status,
            "esquina_score": self.esquina_norm_score,
            "esquina_error": self.esquina_norm_error,
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
