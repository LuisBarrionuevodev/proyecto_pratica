from app.database import db


class IniciadorRuta(db.Model):
    __tablename__ = "iniciador_ruta"

    id = db.Column(db.Integer, primary_key=True)
    tipo_iniciador = db.Column(
        db.Enum(
            "RELEVAMIENTO",
            "DENUNCIA",
            "REINSPECCION_NOTIFICACION",
            "VERIFICAR_INFORMAR_OFICIO",
            "RATIFICACION_CLAUSURA_OFICIO",
            "RATIFICACION_DECOMISO_OFICIO",
            name="tipo_iniciador_enum",
        ),
        nullable=False,
        index=True,
    )
    estado_iniciador = db.Column(
        db.Enum(
            "PENDIENTE",
            "PLANIFICADO",
            "EN_EJECUCION",
            "CUMPLIDO",
            "NO_REALIZADO_REPROGRAMAR",
            "CERRADO",
            "CERRADO_NO_EXISTE_LOCAL",
            "ANULADO",
            name="estado_iniciador_enum",
        ),
        nullable=False,
        default="PENDIENTE",
        server_default="PENDIENTE",
        index=True,
    )
    fecha_origen = db.Column(db.Date, nullable=False, index=True)
    anio = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer, nullable=False, index=True)
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    turno_sugerido = db.Column(
        db.Enum("MANIANA", "TARDE", name="tipo_turno"),
        nullable=True,
        index=True,
    )
    prioridad = db.Column(db.SmallInteger, nullable=False, default=1, server_default="1")
    observaciones = db.Column(db.Text, nullable=True)
    cerrado_at = db.Column(db.DateTime, nullable=True)
    cerrado_motivo = db.Column(db.String(255), nullable=True)

    denuncia_id = db.Column(
        db.Integer,
        db.ForeignKey("denuncia.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    relevamiento_id = db.Column(
        db.Integer,
        db.ForeignKey("relevamiento.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    notificacion_id = db.Column(
        db.Integer,
        db.ForeignKey("notificacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    comprobacion_id = db.Column(
        db.Integer,
        db.ForeignKey("comprobacion.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    oficio_id = db.Column(
        db.Integer,
        db.ForeignKey("oficio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
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

    domicilio = db.relationship("Domicilio")
    denuncia = db.relationship("Denuncia")
    relevamiento = db.relationship("Relevamiento")
    notificacion = db.relationship("Notificacion")
    comprobacion = db.relationship("Comprobacion")
    oficio = db.relationship("Oficio")
    actuacion = db.relationship("Actuaciones")
    created_by_user = db.relationship("User")

    ruta_items = db.relationship("RutaItem", back_populates="iniciador_ruta")

    __table_args__ = (
        db.Index("ix_iniciador_ruta_anio_mes_estado", "anio", "mes", "estado_iniciador"),
        db.Index("ix_iniciador_ruta_anio_mes_tipo", "anio", "mes", "tipo_iniciador"),
        db.Index(
            "ix_iniciador_ruta_anio_mes_turno_estado",
            "anio",
            "mes",
            "turno_sugerido",
            "estado_iniciador",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tipo_iniciador": self.tipo_iniciador,
            "estado_iniciador": self.estado_iniciador,
            "fecha_origen": self.fecha_origen.isoformat() if self.fecha_origen else None,
            "anio": self.anio,
            "mes": self.mes,
            "domicilio_id": self.domicilio_id,
            "turno_sugerido": self.turno_sugerido,
            "prioridad": self.prioridad,
            "observaciones": self.observaciones,
            "cerrado_at": self.cerrado_at.isoformat() if self.cerrado_at else None,
            "cerrado_motivo": self.cerrado_motivo,
            "denuncia_id": self.denuncia_id,
            "relevamiento_id": self.relevamiento_id,
            "notificacion_id": self.notificacion_id,
            "comprobacion_id": self.comprobacion_id,
            "oficio_id": self.oficio_id,
            "actuacion_id": self.actuacion_id,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
