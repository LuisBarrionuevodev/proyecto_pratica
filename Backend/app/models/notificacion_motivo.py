from app.database import db

notificacion_motivo = db.Table(
    "notificacion_motivo",
    db.Column(
        "notificacion_id",
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "motivo",
        db.Integer,
        db.ForeignKey("motivo.id", ondelete="CASCADE"),
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
