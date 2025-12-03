from app.database import db


class Barrio(db.Model):
    __tablename__ = "barrio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), nullable=False)

    distrito_id = db.Column(
        db.Integer,
        db.ForeignKey("distrito.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )

    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.TIMESTAMP,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    distrito = db.relationship("distrito", back_populate="barrio")
    domicilio = db.relationship("domicilio", back_populate="barrio")
