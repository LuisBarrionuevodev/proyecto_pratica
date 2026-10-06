from __future__ import annotations

from datetime import datetime

from app.database import db


class CompletarTrabajoCierreIdempotency(db.Model):
    """Registro de cierre idempotente por RutaItem + clave cliente."""

    __tablename__ = "completar_trabajo_cierre_idempotency"

    id = db.Column(db.Integer, primary_key=True)
    ruta_item_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_item.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key = db.Column(db.String(64), nullable=False)
    payload_digest = db.Column(db.String(64), nullable=False)
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(),
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "ruta_item_id",
            "idempotency_key",
            name="uq_completar_trabajo_cierre_idem_item_key",
        ),
    )
