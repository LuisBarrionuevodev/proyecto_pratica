from __future__ import annotations

from datetime import datetime

from app.database import db


class ContribuyenteDocumentoUnico(db.Model):
    """
    Reserva de documento normalizado para el canal de corrección A2.

    Garantiza que dos correcciones concurrentes no asignen el mismo CUIT/DNI
    normalizado a contribuyentes distintos. No reemplaza un unique sobre
    ``contribuyente.documento`` (pueden existir duplicados históricos).
    """

    __tablename__ = "contribuyente_documento_unico"

    documento_normalizado = db.Column(db.String(32), primary_key=True)
    contribuyente_id = db.Column(
        db.Integer,
        db.ForeignKey("contribuyente.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    contribuyente = db.relationship("Contribuyente")
