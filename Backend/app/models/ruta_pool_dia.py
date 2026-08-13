from app.database import db


class RutaPoolDia(db.Model):
    """
    Staging persistente del pool operativo del día (OPER-RUTA.2).

    No reemplaza ``RutaGrupo`` ni ``RutaItem``; registra intención de planificar
    antes de asignar a una ruta en BORRADOR.
    """

    __tablename__ = "ruta_pool_dia"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    turno_id = db.Column(
        db.Integer,
        db.ForeignKey("turno.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    origen_tipo = db.Column(
        db.Enum(
            "INICIADOR",
            "ACTUACION_NOTIF",
            "ACTUACION_COMP",
            "RELEVAMIENTO",
            "DENUNCIA",
            "MANUAL",
            name="ruta_pool_dia_origen_tipo_enum",
        ),
        nullable=False,
        index=True,
    )
    iniciador_ruta_id = db.Column(
        db.Integer,
        db.ForeignKey("iniciador_ruta.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    actuacion_id = db.Column(
        db.Integer,
        db.ForeignKey("actuaciones.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    distrito_id = db.Column(
        db.Integer,
        db.ForeignKey("distrito.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    estado = db.Column(
        db.Enum(
            "EN_POOL",
            "ASIGNADO_A_RUTA",
            "DESCARTADO",
            name="ruta_pool_dia_estado_enum",
        ),
        nullable=False,
        default="EN_POOL",
        server_default="EN_POOL",
        index=True,
    )
    ruta_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_trabajo.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    ruta_item_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_item.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    observacion = db.Column(db.Text, nullable=True)
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
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    usuario = db.relationship("User", foreign_keys=[usuario_id])
    iniciador_ruta = db.relationship("IniciadorRuta")
    domicilio = db.relationship("Domicilio")
    distrito = db.relationship("Distrito")
    rubro = db.relationship("Rubro")
    ruta_trabajo = db.relationship("RutaTrabajo")
    ruta_item = db.relationship("RutaItem")

    __table_args__ = (
        db.Index(
            "ix_ruta_pool_dia_fecha_estado_distrito_rubro",
            "fecha",
            "estado",
            "distrito_id",
            "rubro_id",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "turno_id": self.turno_id,
            "usuario_id": self.usuario_id,
            "origen_tipo": self.origen_tipo,
            "iniciador_ruta_id": self.iniciador_ruta_id,
            "actuacion_id": self.actuacion_id,
            "domicilio_id": self.domicilio_id,
            "distrito_id": self.distrito_id,
            "rubro_id": self.rubro_id,
            "estado": self.estado,
            "ruta_trabajo_id": self.ruta_trabajo_id,
            "ruta_item_id": self.ruta_item_id,
            "observacion": self.observacion,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
