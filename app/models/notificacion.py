from sqlalchemy import event

from app.database import db


class Notificacion(db.Model):
    __tablename__ = "notificacion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    actuaciones = db.relationship("Actuaciones", back_populates="notificacion")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_an_numero_anio"),
        db.Index("idx_notificacion_mes", "mes"),
        db.Index("idx_notificacion_anio", "anio"),
    )


@event.listens_for(Notificacion, "before_insert")
def set_notificacion_anio(mapper, connection, target):
    if target.actuaciones:
        target.anio = target.actuaciones.anio
        target.mes = target.actuaciones.mes
