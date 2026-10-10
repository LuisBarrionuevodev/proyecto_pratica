from __future__ import annotations

from datetime import datetime

from app.database import db


class RutaItemArchivo(db.Model):
    """Vínculo funcional entre un ítem de ruta y un archivo categorizado."""

    __tablename__ = "ruta_item_archivo"

    id = db.Column(db.Integer, primary_key=True)
    ruta_item_id = db.Column(
        db.Integer,
        db.ForeignKey("ruta_item.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    archivo_id = db.Column(
        db.Integer,
        db.ForeignKey("archivo.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria = db.Column(
        db.Enum(
            "FOTO_ACTA",
            "FOTO_DOCUMENTACION_LOCAL",
            "FOTO_INSPECCION",
            name="ruta_item_archivo_categoria_enum",
        ),
        nullable=False,
        index=True,
    )
    tipo_documento = db.Column(
        db.Enum(
            "ACTA_INSPECCION",
            "ACTA_NOTIFICACION",
            "OTRO_ACTA",
            "HABILITACION",
            "CARNET_MANIPULADOR",
            "CERTIFICADO_DESINFECCION",
            "OTRO_DOCUMENTO_LOCAL",
            name="ruta_item_archivo_tipo_documento_enum",
        ),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(),
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )
    content_sha256 = db.Column(db.String(64), nullable=True, index=True)
    upload_origin = db.Column(
        db.Enum(
            "COMPLETAR_TRABAJO",
            "MIS_TRABAJOS",
            name="ruta_item_archivo_upload_origin_enum",
        ),
        nullable=True,
        server_default="COMPLETAR_TRABAJO",
    )

    archivo = db.relationship("Archivo", back_populates="ruta_item_links")
    ruta_item = db.relationship("RutaItem", backref=db.backref("archivos_vinculo", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("ruta_item_id", "archivo_id", name="uq_ruta_item_archivo_pair"),
        db.Index("ix_ruta_item_archivo_item_categoria", "ruta_item_id", "categoria"),
        db.Index(
            "uq_ruta_item_archivo_item_cat_sha",
            "ruta_item_id",
            "categoria",
            "content_sha256",
            unique=True,
        ),
    )
