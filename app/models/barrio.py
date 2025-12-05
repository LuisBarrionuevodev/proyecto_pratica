from geoalchemy2 import Geometry

from app.database import db


class Barrio(db.Model):
    __tablename__ = "barrio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )
    geom = db.Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)

    distrito_id = db.Column(
        db.Integer,
        db.ForeignKey("distrito.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
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
    distrito = db.relationship("Distrito", back_populates="barrio")
    domicilio = db.relationship("Domicilio", back_populates="barrio")
    __table_args__ = (db.Index("idx_barrio_geom", "geom", mysql_prefix="SPATIAL"),)
