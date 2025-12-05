from sqlalchemy import event

from app.database import db


class Comprobacion(db.Model):
    __tablename__ = "comprobacion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False, index=True)
    motivo = db.Column(
        db.Text,
        nullable=False,
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
    actuacion = db.relationship("Actuaciones", back_populates="acta_comprobacion")
    oficio = db.relationship("Oficio", back_populates="comprobacion")
    expediente = db.relationship("Expediente", back_populates="comprobacion")
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_acomp_numero_anio"),
        db.Index("idx_comprobacion_mes", "mes"),
        db.Index("idx_comprobacion_anio", "anio"),
    )


@event.listens_for(Comprobacion, "before_insert")
def set_comprobacion_anio(mapper, connection, target):
    if target.actuaciones:
        target.anio = target.actuaciones.anio
        target.mes = target.actuaciones.mes
