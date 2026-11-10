from app.database import db

comprobacion_motivo = db.Table(
    "comprobacion_motivo",
    db.Column(
        "comprobacion_id",
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "catalog_motivo_comprobacion_id",
        db.Integer,
        db.ForeignKey("catalog_motivo_comprobacion.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    db.Column(
        "created_at",
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    ),
    db.Column(
        "updated_at",
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    ),
    db.Column("deleted_at", db.DateTime, nullable=True),
)
