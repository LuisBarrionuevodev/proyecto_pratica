from __future__ import annotations

from app.database import db


class ActuacionMedia(db.Model):
    """
    Referencias a evidencias (foto/video/audio) asociadas a una actuación.
    URLs externas (p. ej. EpiCollect); sin blobs en esta fase.
    """

    __tablename__ = "actuacion_media"

    id = db.Column(db.Integer, primary_key=True)
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria = db.Column(db.String(64), nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    mime_type = db.Column(db.String(128), nullable=True)
    orden = db.Column(db.SmallInteger, nullable=False, default=0, server_default="0")
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

    actuacion = db.relationship("Actuaciones", back_populates="actuacion_media_items")
