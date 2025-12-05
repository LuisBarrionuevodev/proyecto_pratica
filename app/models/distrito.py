from geoalchemy2 import Geometry

from app.database import db


class Distrito(db.Model):
    __tablename__ = "distrito"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # Polígono real
    geom = db.Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)

    barrio = db.relationship("Barrio", back_populates="distrito")

    __table_args__ = (db.Index("idx_distrito_geom", "geom", mysql_prefix="SPATIAL"),)
