import enum

from sqlalchemy import Enum

from app.database import db


class ContraEnum(enum.Enum):
    LOCAL_CERRADO = "LOCAL CERRADO"
    NO_EXISTE = "NO EXISTE/NO ES EL RUBRO"
    INCLEMENCIA_TIEMPO = "CLIMA"
    ZONA_ROJA = "ZONA ROJA"
    NO_HUBO = "NO_HUBO"
    OTROS = "OTROS"


class Actuaciones(db.Model):
    __tablename__ = "actuaciones"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)

    orden_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("orden_trabajo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=False,
        unique=True,
    )
    notificacion_id = db.Column(
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )

    contraproducencia = db.Column(
        Enum(ContraEnum, name="contra_enum", native_enum=False),
        nullable=True,
        default=ContraEnum.NO_HUBO,
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
    notificacion = db.relationship("notificacion", back_populates="actuaciones")
    orden_trabajo = db.relationship("orden_trabajo", back_populates="actuaciones")
    acta_comprobacion = db.relationship(
        "acta_comprobacion", back_populates="actuaciones"
    )
    domicilio = db.relationship("domicilio", back_populates="actuaciones")
