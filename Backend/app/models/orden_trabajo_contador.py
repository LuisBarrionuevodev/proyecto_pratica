from __future__ import annotations

from app.database import db


class OrdenTrabajoContador(db.Model):
    """Singleton lógico: una fila con el próximo valor de secuencia global OT."""

    __tablename__ = "orden_trabajo_contador"

    id = db.Column(db.Integer, primary_key=True)
    next_value = db.Column(db.BigInteger, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class OrdenTrabajoContadorAudit(db.Model):
    """Auditoría append-only de cambios manuales al contador (solo admin)."""

    __tablename__ = "orden_trabajo_contador_audit"

    id = db.Column(db.Integer, primary_key=True)
    old_value = db.Column(db.BigInteger, nullable=False)
    new_value = db.Column(db.BigInteger, nullable=False)
    requested_new_value = db.Column(db.BigInteger, nullable=True)
    reason = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
