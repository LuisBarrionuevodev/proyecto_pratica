from __future__ import annotations

from datetime import datetime

from app.database import db


class Archivo(db.Model):
    """Metadata de un objeto en storage privado (sin binario en MySQL)."""

    __tablename__ = "archivo"

    id = db.Column(db.Integer, primary_key=True)
    storage_provider = db.Column(db.String(32), nullable=False)
    bucket = db.Column(db.String(128), nullable=False)
    object_key = db.Column(db.String(512), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(128), nullable=False)
    byte_size = db.Column(db.BigInteger(), nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    status = db.Column(
        db.Enum(
            "PENDING",
            "READY",
            "REJECTED",
            "DELETED",
            name="archivo_status_enum",
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )
    uploaded_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(),
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )
    uploaded_at = db.Column(db.DateTime(), nullable=True)
    deleted_at = db.Column(db.DateTime(), nullable=True)
    deleted_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    ruta_item_links = db.relationship(
        "RutaItemArchivo",
        back_populates="archivo",
        lazy="select",
    )
