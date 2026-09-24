"""
Detalle no-media importado desde EpiCollect5 (snapshot JSON local).

Una fila por actuación (`actuacion_id` único). El cuerpo útil vive en `payload_non_media`.
"""

from __future__ import annotations

from app.database import db


class ActuacionEpicollectDetalle(db.Model):
    __tablename__ = "actuacion_epicollect_detalle"

    id = db.Column(db.Integer, primary_key=True)
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    entry_uuid = db.Column(db.String(36), nullable=False, index=True)
    source = db.Column(
        db.String(32),
        nullable=False,
        default="EPICOLLECT",
        server_default="EPICOLLECT",
    )
    payload_non_media = db.Column(db.JSON, nullable=False)
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

    actuacion = db.relationship("Actuaciones", back_populates="epicollect_detalle")
