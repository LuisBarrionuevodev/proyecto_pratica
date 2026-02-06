from app.database import db


class DomicilioGeocode(db.Model):
    __tablename__ = "domicilio_geocode"

    domicilio_id = db.Column(
        db.Integer,
        db.ForeignKey("domicilio.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )

    lat = db.Column(db.Numeric(10, 7), nullable=True)
    lng = db.Column(db.Numeric(10, 7), nullable=True)
    geo_status = db.Column(
        db.Enum("PENDING", "OK", "REVIEW", "NO_MATCH", "ERROR", name="domicilio_geocode_status"),
        nullable=False,
        default="PENDING",
        index=True,
    )
    provider = db.Column(db.String(50), nullable=True)
    quality = db.Column(db.String(30), nullable=True)
    score = db.Column(db.Float, nullable=True)
    error_msg = db.Column(db.String(255), nullable=True)
    raw_json = db.Column(db.JSON, nullable=True)
    addr_hash = db.Column(db.String(40), nullable=True)
    source = db.Column(
        db.Enum("AUTO", "MANUAL", "REVERSE", name="domicilio_geocode_source"),
        nullable=True,
        default="AUTO",
    )
    checked_at = db.Column(db.DateTime, nullable=True)

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

    domicilio = db.relationship("Domicilio", back_populates="geocode")
