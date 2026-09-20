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
        nullable=True,
    )
    valor_si_no = db.Column(db.Boolean, nullable=True)

    inspeccion = db.relationship("Inspeccion", back_populates="checklist_items")
    item = db.relationship("ItemActaInspeccion", back_populates="inspeccion_junctions")

    __table_args__ = (
        db.UniqueConstraint(
            "acta_inspeccion_id",
            "item_acta_inspeccion_id",
            name="uq_acta_inspeccion_item",
        ),
        db.CheckConstraint(
            "(estado IS NOT NULL AND valor_si_no IS NULL) OR "
            "(estado IS NULL AND valor_si_no IS NOT NULL)",
            name="ck_acta_inspeccion_item_xor_respuesta",
        ),
    )
