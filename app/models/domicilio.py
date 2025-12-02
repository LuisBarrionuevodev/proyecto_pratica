from app.database import db


class Domicilio(db.Model):
    __tablename__ = "domicilio"
    id = db.Column(db.Integer, primary_key=True)

    calle = db.Column(db.String(128), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    cp = db.Column(db.String(10), nullable=True, default="4000")
    barrio_id = db.Column(
        db.Integer,
        db.ForeignKey(ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        unique=False,
    )
    contribuyente = db.Column(
        db.Integer,
        db.ForeignKey(ondelete="SET NULL", onupdate="CASCADE"),
        nullable=False,
        unique=False,
    )
    rubro = db.Column(
        db.Integer,
        db.Foreignkey(ondelete="SET NULL", onupdate="CASCADE"),
        nullable=False,
        unique=False,
    )
    lat = db.Column(db.Numeric(9, 6), nullable=True)
    long = db.Column(db.Numeric(9, 6), nullable=True)
    created_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        nullable=False,
    )
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
        nullable=False,
    )

    actuaciones = db.relationship("actuaciones", back_populates="domicilio")
    barrio = db.relationship("barrio", back_populates="domicilio")
    contribuyente = db.relationship("contribuyente", back_populates="domicilio")
