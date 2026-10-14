"""Registro de control e idempotencia para migración histórica (V1.1-MIG-ACTAS.1A)."""

from __future__ import annotations

from datetime import datetime

from app.database import db


class MigracionHistoricaRegistro(db.Model):
    """
    Trazabilidad de importación histórica sin PII ni payload completo.

    Unicidad por fuente + hash de artefactos + UUID de registro (ec5_uuid).
    """

    __tablename__ = "migracion_historica_registro"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(64), nullable=False, index=True)
    source_name = db.Column(db.String(128), nullable=False, index=True)
    source_sha256 = db.Column(db.String(64), nullable=False, index=True)
    source_record_uuid = db.Column(db.String(36), nullable=False, index=True)
    decision = db.Column(db.String(32), nullable=False, index=True)
    target_actuacion_id = db.Column(db.Integer, nullable=True, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.current_timestamp(),
    )
    error_code = db.Column(db.String(64), nullable=True)
    error_detail_sanitized = db.Column(db.String(512), nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "source_name",
            "source_sha256",
            "source_record_uuid",
            name="uq_migracion_hist_fuente_uuid",
        ),
    )
