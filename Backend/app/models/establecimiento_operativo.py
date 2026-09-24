from __future__ import annotations

from app.database import db


class EstablecimientoOperativo(db.Model):
    """
    Ficha de establecimiento operativo (Bromatología): ancla 1:1 en ``domicilio``.

    Distinto de la tabla legacy ``establecimientos`` (eventos / nombre único global).
    """

    __tablename__ = "establecimiento_operativo"

    id = db.Column(db.Integer, primary_key=True)
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
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

    domicilio = db.relationship("Domicilio", back_populates="establecimiento_operativo")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])
    actuaciones = db.relationship("Actuaciones", back_populates="establecimiento_operativo")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "domicilio_id": self.domicilio_id,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
