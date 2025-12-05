from app.database import db


class Domicilio(db.Model):
    __tablename__ = "domicilio"
    id = db.Column(db.Integer, primary_key=True)

    calle = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )
    numero = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )
    cp = db.Column(db.String(10), nullable=True, default="4000")
    barrio_id = db.Column(
        db.Integer,
        db.ForeignKey("barrio.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        unique=False,
        index=True,
    )
    contribuyente = db.Column(
        db.Integer,
        db.ForeignKey("contribuyete.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
    )
    rubro = db.Column(
        db.Integer,
        db.ForeignKey("rubro.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        unique=False,
        index=True,
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

    actuaciones = db.relationship("Actuaciones", back_populates="domicilio")
    barrio = db.relationship("Barrio", back_populates="domicilio")
    contribuyente = db.relationship("Contribuyente", back_populates="domicilio")
    relevamiento = db.relationship("Relevamiento", back_populates="domicilio")
