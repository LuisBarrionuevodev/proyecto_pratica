from app.database import db

relevamiento_relevador = db.Table(
    "relevamiento_relevador",
    db.Column(
        "relevamiento_id",
        db.Integer,
        db.ForeignKey("relevamiento.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "relevador_id",
        db.Integer,
        db.ForeignKey("relevador.id", ondelete="RESTRICT"),
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
)
