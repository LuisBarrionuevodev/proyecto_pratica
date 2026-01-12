from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape

from app.database import db


class Distrito(db.Model):
    __tablename__ = "distrito"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # Polígono real
    geom = db.Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=True)

    barrio = db.relationship("Barrio", back_populates="distrito")

    

    def to_dict(self, include_relations=False, include_geom=False):
        data = {
            "id": self.id,
            "nombre": self.nombre,
        }

        # Geometría en WKT
        if include_geom:
            if self.geom:
                try:
                    data["geom_wkt"] = to_shape(self.geom).wkt
                except Exception:
                    data["geom_wkt"] = None
            else:
                data["geom_wkt"] = None

        if include_relations:
            barrios = []
            if self.barrio:
                for b in self.barrio:
                    barrios.append(b.to_dict())
            data["barrios"] = barrios

        return data
