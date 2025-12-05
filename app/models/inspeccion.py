from sqlalchemy import event

from app.database import db


class Inspeccion(db.Model):
    __tablename__ = "inspeccion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    db.relationship("Actuaciones", back_populates="inspeccion")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_ai_numero_anio"),
        db.Index("idx_inspeccion_mes", "mes"),
        db.Index("idx_inspeccion_anio", "anio"),
    )


@event.listens_for(Inspeccion, "before_insert")
def set_inspeccion_anio(mapper, connection, target):
    if target.actuaciones:
        target.anio = target.actuaciones.anio
        target.mes = target.actuaciones.mes
