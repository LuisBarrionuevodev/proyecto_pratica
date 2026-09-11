from app.database import db


class ActaInspeccionItem(db.Model):
    """Junction Inspección ↔ ítem de checklist con estado BIEN/OBSERVADO."""

    __tablename__ = "acta_inspeccion_item"

    acta_inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_acta_inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("item_acta_inspeccion.id", ondelete="CASCADE"),
        primary_key=True,
    )
    estado = db.Column(
        db.Enum("BIEN", "OBSERVADO", name="item_inspeccion_estado_enum"),
        nullable=False,
    )

    inspeccion = db.relationship("Inspeccion", back_populates="checklist_items")
    item = db.relationship("ItemActaInspeccion", back_populates="inspeccion_junctions")

    __table_args__ = (
        db.UniqueConstraint(
            "acta_inspeccion_id",
            "item_acta_inspeccion_id",
            name="uq_acta_inspeccion_item",
        ),
    )
