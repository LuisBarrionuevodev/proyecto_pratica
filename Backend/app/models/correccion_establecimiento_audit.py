from __future__ import annotations

from datetime import datetime

from app.database import db


class CorreccionEstablecimientoAudit(db.Model):
    """
    Auditoría de correcciones controladas de contribuyente/domicilio
    desde la ficha de establecimiento operativo.
    """

    __tablename__ = "correccion_establecimiento_audit"

    id = db.Column(db.Integer, primary_key=True)
    establecimiento_operativo_id = db.Column(
        db.Integer,
        db.ForeignKey("establecimiento_operativo.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    contribuyente_id = db.Column(
        db.Integer,
        db.ForeignKey("contribuyente.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    tipo = db.Column(
        db.Enum(
            "CONTRIBUYENTE",
            "DOMICILIO",
            "AMBOS",
            "LOCAL",
            name="correccion_establecimiento_tipo_enum",
        ),
        nullable=False,
        index=True,
    )
    valores_anteriores = db.Column(db.JSON, nullable=False)
    valores_nuevos = db.Column(db.JSON, nullable=False)
    alcance = db.Column(db.JSON, nullable=False)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.current_timestamp(),
    )

    establecimiento_operativo = db.relationship("EstablecimientoOperativo")
    contribuyente = db.relationship("Contribuyente")
    domicilio = db.relationship("Domicilio")
    created_by_user = db.relationship("User")
