from app.database import db


class NotificacionResultadoReinspeccion(db.Model):
    __tablename__ = "notificacion_resultado_reinspeccion"

    id = db.Column(db.Integer, primary_key=True)
    notificacion_id = db.Column(
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    faltas_subsanadas = db.Column(db.Boolean, nullable=False)
    fecha_verificacion = db.Column(db.Date, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    notificacion = db.relationship("Notificacion")
    actuacion = db.relationship("Actuaciones")
    inspeccion = db.relationship("Inspeccion")
