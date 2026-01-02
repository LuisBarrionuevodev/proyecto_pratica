from __future__ import annotations

from datetime import datetime
import sqlalchemy as sa

from app.database import db
from app.models.enums import Tipo, ContraEnum


class Actuaciones(db.Model):
    __tablename__ = "actuaciones"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=datetime.now)
    mes = db.Column(db.Integer, nullable=False, index=True)
    anio = db.Column(db.Integer, nullable=False, index=True)

    # ✅ Guardar/leer por .value (ej "RATIFICACION DE CLAUSURA")
    tipo = db.Column(
        sa.Enum(
            Tipo,
            name="tipo_actuacion",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=True,   # MySQL ENUM real (como tu tabla ya tiene)
        ),
        nullable=True,
        default=None,
        index=True,
    )

    contraproducencia = db.Column(
        sa.Enum(
            ContraEnum,
            name="contraproducencia",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=True,
        ),
        nullable=True,
        default=ContraEnum.NO_HUBO,
        index=True,
    )

    # --- FKs (tal cual tu modelo) ---
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

    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    # --- relationships (tal cual tu modelo) ---
    notificacion = db.relationship("Notificacion", back_populates="actuaciones")
    orden_trabajo = db.relationship("OrdenTrabajo", back_populates="actuaciones")
    comprobacion = db.relationship("Comprobacion", back_populates="actuaciones")
    domicilio = db.relationship("Domicilio", back_populates="actuaciones")

    clausura = db.relationship(
        "Clausura",
        back_populates="actuaciones",
        uselist=False,
        cascade="all, delete-orphan",
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
        "Inspector",
        secondary="actuaciones_inspector",
        back_populates="actuaciones",
    )

    __table_args__ = (db.Index("idx_tipo_mes_anio", "tipo", "mes", "anio"),)

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "mes": self.mes,
            "anio": self.anio,
            "tipo": self.tipo.value if self.tipo else None,
            "contraproducencia": self.contraproducencia.value if self.contraproducencia else None,
            "orden_trabajo_id": self.orden_trabajo_id,
            "notificacion_id": self.notificacion_id,
            "comprobacion_id": self.comprobacion_id,
            "domicilio_id": self.domicilio_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_relations:
            data["orden_trabajo"] = self.orden_trabajo.to_dict() if self.orden_trabajo else None
            data["notificacion"] = self.notificacion.to_dict() if self.notificacion else None
            data["comprobacion"] = self.comprobacion.to_dict() if self.comprobacion else None
            data["domicilio"] = self.domicilio.to_dict() if self.domicilio else None
            data["clausura"] = self.clausura.to_dict() if self.clausura else None
            data["decomiso"] = self.decomiso.to_dict() if self.decomiso else None
            data["inspeccion"] = self.inspeccion.to_dict() if self.inspeccion else None

        return data
