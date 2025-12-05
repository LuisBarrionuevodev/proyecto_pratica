from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape

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

    def to_dict(self, include_relations=False, include_geom=False):
        data = {
            "id": self.id,
            "nombre": self.nombre,
            "distrito_id": self.distrito_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_geom:
            if self.geom:
                try:
                    data["geom_wkt"] = to_shape(self.geom).wkt
                except Exception:
                    data["geom_wkt"] = None
            else:
                data["geom_wkt"] = None
        if include_relations:
            data["distrito"] = self.distrito.to_dict() if self.distrito else None

            domicilios = []
            if self.domicilio:
                for d in self.domicilio:
                    domicilios.append(d.to_dict())

            data["domicilios"] = domicilios

        return data
