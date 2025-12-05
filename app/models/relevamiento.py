from sqlalchemy import event

from app.database import db


class Relevamiento(db.Model):
    __tablename__ = "relevamiento"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    anio = db.Column(db.Date, nullable=False)
    mes = db.Column(db.Date, nullable=False)

    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    rubro_id = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
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

    domicilio = db.relationship("Domicilio", back_populates="relevamiento")
    rubro = db.relationship("Rubro", back_populates="relevamiento")
    __table_args__ = (
        db.Index("idx_relevamiento_mes", "mes"),
        db.Index("idx_relevamiento_anio", "anio"),
    )


@event.listens_for(Relevamiento, "before_insert")
@event.listens_for(Relevamiento, "before_update")
def sync_mes_anio(mapper, connection, target):
    if target.fecha:
        target.mes = target.fecha.month
        target.anio = target.fecha.year
