from sqlalchemy import event

from app.database import db


class Clausura(db.Model):
    __tablename__ = "clausura"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
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
    actuacion = db.relationship("Actuaciones", back_populates="clausura")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_ac_numero_anio"),
        db.Index("idx_clausura_mes", "mes"),
        db.Index("idx_clausura_anio", "anio"),
    )


@event.listens_for(Clausura, "before_insert")
def set_clausura_anio(mapper, connection, target):
    if target.actuaciones:
        target.anio = target.actuaciones.anio
        target.mes = target.actuaciones.mes
