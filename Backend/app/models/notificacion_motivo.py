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
)
