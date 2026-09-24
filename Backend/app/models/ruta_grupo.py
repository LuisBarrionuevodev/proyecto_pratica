from app.database import db


class RutaGrupo(db.Model):
    __tablename__ = "ruta_grupo"

    id = db.Column(db.Integer, primary_key=True)
    ruta_trabajo_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_trabajo.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre = db.Column(db.String(120), nullable=False)
    estado = db.Column(db.String(32), nullable=True)
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
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    ruta_trabajo = db.relationship("RutaTrabajo", back_populates="grupos")
    created_by_user = db.relationship("User")
    grupo_inspectores = db.relationship("RutaGrupoInspector", back_populates="ruta_grupo")
    items = db.relationship("RutaItem", back_populates="ruta_grupo")

    __table_args__ = (
        db.UniqueConstraint("ruta_trabajo_id", "nombre", name="uq_ruta_grupo_ruta_nombre"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ruta_trabajo_id": self.ruta_trabajo_id,
            "nombre": self.nombre,
            "estado": self.estado,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
