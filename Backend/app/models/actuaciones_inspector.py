from app.database import db

actuaciones_inspector = db.Table(
    "actuaciones_inspector",
    db.Column(
        "actuaciones_id",
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "inspector_id",
        db.Integer,
        db.ForeignKey("inspector.id", ondelete="CASCADE"),
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
