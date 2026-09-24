from app.database import db


class RutaGrupoInspector(db.Model):
    __tablename__ = "ruta_grupo_inspector"

    id = db.Column(db.Integer, primary_key=True)
    ruta_grupo_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_grupo.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    inspector_id = db.Column(
        db.Integer,
        db.ForeignKey("inspector.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
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

    ruta_grupo = db.relationship("RutaGrupo", back_populates="grupo_inspectores")
    inspector = db.relationship("Inspector")
    created_by_user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("ruta_grupo_id", "inspector_id", name="uq_ruta_grupo_inspector"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ruta_grupo_id": self.ruta_grupo_id,
            "inspector_id": self.inspector_id,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
