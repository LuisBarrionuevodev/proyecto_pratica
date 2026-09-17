"""Cola durable de geocode post-commit (GEO-PERF.1 / 1.1)."""



from __future__ import annotations



from datetime import datetime



from app.database import db





class GeocodePostCommitJob(db.Model):

    """

    Trabajo pendiente para ejecutar ``pipeline_post_commit`` fuera del HTTP request.



    Un domicilio solo puede tener un job ``pending`` o ``processing`` a la vez.

    El claim atómico usa ``SELECT ... FOR UPDATE SKIP LOCKED`` + update condicional.

    """



    __tablename__ = "geocode_post_commit_job"



    id = db.Column(db.Integer, primary_key=True)

    domicilio_id = db.Column(db.Integer, db.ForeignKey("domicilio.id"), nullable=False, index=True)

    status = db.Column(

        db.Enum("pending", "processing", "done", "failed", name="geocode_post_commit_job_status"),

        nullable=False,

        default="pending",

        index=True,

    )

    attempts = db.Column(db.Integer, nullable=False, default=0)

    last_error = db.Column(db.String(500), nullable=True)

    processing_started_at = db.Column(db.DateTime, nullable=True)

    claimed_addr_hash = db.Column(db.String(40), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    updated_at = db.Column(

        db.DateTime,

        nullable=False,

        default=datetime.utcnow,

        onupdate=datetime.utcnow,

    )



    domicilio = db.relationship("Domicilio", backref=db.backref("geocode_post_commit_jobs", lazy="dynamic"))



    __table_args__ = (

        db.Index("ix_geocode_post_commit_job_status_created", "status", "created_at"),

        db.Index("ix_geocode_post_commit_job_domicilio_status", "domicilio_id", "status"),

    )

