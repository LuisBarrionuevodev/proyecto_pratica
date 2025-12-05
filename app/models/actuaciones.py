import enum
from datetime import datetime

from sqlalchemy import Enum, event

from app.database import db
from app.models import actuaciones_inspector


class ContraEnum(enum.Enum):
    LOCAL_CERRADO = "LOCAL CERRADO"
    NO_EXISTE = "NO EXISTE/NO ES EL RUBRO"
    INCLEMENCIA_TIEMPO = "CLIMA"
    ZONA_ROJA = "ZONA ROJA"
    NO_HUBO = "NO_HUBO"
    OTROS = "OTROS"


class Tipo(enum.Enum):
    INSPECCION = "INSPECCION"
    REINSPECCION = "REINSPECCION"
    RATIFICACION_CLAUSURA = "RATIFICACION DE CLAUSURA"
    RATIFICACION_DECOMISO = "RATIFICACION DE DECOMISO"
    VERIFICAR_E_IFORMAR = "VERIFICAR E INFORMAR"


class Actuaciones(db.Model):
    __tablename__ = "actuaciones"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=datetime.now())
    mes = db.Column(db.Integer, nullable=False, index=True)
    anio = db.Column(db.Integer, nullable=False, index=True)

    tipo = db.Column(
        Enum(Tipo, name="tipo", native_enum=False),
        nullable=True,
        default=Tipo.INSPECCION,
        index=True,
    )

    orden_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("orden_trabajo.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    notificacion_id = db.Column(
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )

    contraproducencia = db.Column(
        Enum(ContraEnum, name="contra_enum", native_enum=False),
        nullable=True,
        default=ContraEnum.NO_HUBO,
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
    notificacion = db.relationship("Notificacion", back_populates="actuaciones")
    orden_trabajo = db.relationship("OrdenTrabajo", back_populates="actuaciones")
    acta_comprobacion = db.relationship("Comprobacion", back_populates="actuaciones")
    domicilio = db.relationship("Domicilio", back_populates="actuaciones")
    clausura = db.relationship(
        "Clausura",
        back_populates="actuaciones",
        uselist=False,
        cascade="all, delete-orphan",  ##si borro la actuacion se borra la clausura
    )
    decomiso = db.relationship(
        "Decomiso",
        back_populates="actuaciones",
        uselist=False,
        cascade="all, delete-orphan",
    )

    inspeccion = db.relationship(
        "Inspeccion",
        back_populates="actuaciones",
        uselist=False,
        cascade="all, delete-orphan",
    )
    inspector = db.relationship(
        "Inspector", secondary=actuaciones_inspector, back_populates="actuaciones"
    )
    _table_args__ = (
        db.Index("idx_tipo_mes_anio", "tipo", "mes", "anio"),
        db.Index("idx_actuacion_mes", "mes"),
        db.Index("idx_actuacion_anio", "anio"),
    )


@event.listens_for(Actuaciones, "before_insert")
@event.listens_for(Actuaciones, "before_update")
def sync_mes_anio(mapper, connection, target):
    if target.fecha:
        target.mes = target.fecha.month
        target.anio = target.fecha.year
