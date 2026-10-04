from app.database import db


class SolicitudCarnetManipulador(db.Model):
    __tablename__ = "solicitud_carnet_manipulador"

    id = db.Column(db.Integer, primary_key=True)
    contribuyente_id = db.Column(
        db.Integer,
        db.ForeignKey("contribuyente.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    solicita_carnet = db.Column(db.Boolean, nullable=False)
    telefono_contacto = db.Column(db.String(32), nullable=True)
    fecha_solicitud = db.Column(db.Date, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    contribuyente = db.relationship("Contribuyente")
    inspeccion = db.relationship("Inspeccion")
