from sqlalchemy import event

from app.database import db


class Relevamiento(db.Model):
    __tablename__ = "relevamiento"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
    turno_carga = db.Column(
        db.Enum("MANIANA", "TARDE", name="tipo_turno"),
        nullable=True,
        index=True,
    )
    esta_abierto = db.Column(db.Boolean, nullable=True, index=True)

    inspector_id = db.Column(
        db.Integer,
        db.ForeignKey("inspector.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    nombre_fantasia = db.Column(db.String(255), nullable=True)
    angulo_esquina = db.Column(db.String(10), nullable=True)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
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
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    inspector = db.relationship("Inspector", back_populates="relevamientos")
    domicilio = db.relationship("Domicilio", back_populates="relevamiento")
    rubro = db.relationship("Rubro", back_populates="relevamiento")
    created_by_user = db.relationship("User")

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "fecha": self.fecha,
            "anio": self.anio,
            "mes": self.mes,
            "turno_carga": self.turno_carga,
            "esta_abierto": self.esta_abierto,
            "inspector_id": self.inspector_id,
            "domicilio_id": self.domicilio_id,
            "rubro_id": self.rubro_id,
            "nombre_fantasia": self.nombre_fantasia,
            "angulo_esquina": self.angulo_esquina,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }

        if include_relations:
            data["inspector"] = self.inspector.to_dict() if self.inspector else None
            data["domicilio"] = self.domicilio.to_dict() if self.domicilio else None
            data["rubro"] = self.rubro.to_dict() if self.rubro else None
        return data



