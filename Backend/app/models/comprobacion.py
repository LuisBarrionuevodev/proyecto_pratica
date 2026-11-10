from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models.comprobacion_motivo import comprobacion_motivo

SEPARADOR_TEXTO_MOTIVOS_COMPROBACION = " · "


class Comprobacion(db.Model):
    __tablename__ = "comprobacion"
    id = db.Column(db.Integer, primary_key=True)
    numero_acta = db.Column(
        db.String(6),
        nullable=False,
        index=True,
    )
    anio = db.Column(
        db.Integer, nullable=False, index=True, default=lambda: datetime.now().year
    )
    mes = db.Column(
        db.Integer, nullable=False, index=True, default=lambda: datetime.now().month
    )
    motivo = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )
    deleted_at = db.Column(db.DateTime, nullable=True)
    sin_expediente_envio = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
        index=True,
    )
    sin_expediente_envio_declarado_at = db.Column(db.DateTime, nullable=True)
    sin_expediente_envio_declarado_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    actuaciones = db.relationship("Actuaciones", back_populates="comprobacion")
    oficio = db.relationship("Oficio", back_populates="comprobacion")
    expediente = db.relationship("Expediente", back_populates="comprobacion")
    motivos_catalogo = db.relationship(
        "CatalogMotivoComprobacion",
        secondary=comprobacion_motivo,
        back_populates="comprobaciones",
        order_by="CatalogMotivoComprobacion.nombre",
    )
    __table_args__ = (
        db.UniqueConstraint("numero_acta", "anio", name="uq_acomp_numero_anio"),
    )

    def motivos_comprobacion_ordenados(self):
        """
        Lectura ordenada de motivos de catálogo vinculados (preparada para MOTIVOS.2).

        Returns:
            Lista de `CatalogMotivoComprobacion` ordenada por `nombre`.
        """
        rows = [m for m in (self.motivos_catalogo or []) if m is not None]
        rows.sort(key=lambda m: ((m.nombre or ""), int(m.id or 0)))
        return rows

    def motivos_comprobacion_as_dicts(self) -> list[dict]:
        """
        Forma futura de API: `motivos_comprobacion: [{id, nombre}, ...]`.

        Returns:
            Lista de dicts `{id, nombre}` en el mismo orden que
            `motivos_comprobacion_ordenados`.
        """
        return [{"id": int(m.id), "nombre": m.nombre} for m in self.motivos_comprobacion_ordenados()]

    def texto_derivado_motivos_comprobacion(self) -> str | None:
        """
        Texto derivado futuro para consumidores históricos: `Motivo A · Motivo B`.

        No escribe ni reemplaza la columna legado `motivo`.

        Returns:
            String unido con `SEPARADOR_TEXTO_MOTIVOS_COMPROBACION`, o `None`
            si no hay vínculos.
        """
        nombres = [m.nombre for m in self.motivos_comprobacion_ordenados() if m.nombre]
        if not nombres:
            return None
        return SEPARADOR_TEXTO_MOTIVOS_COMPROBACION.join(nombres)

    def to_dict(self, include_relations=False):
        data = {
            "id": self.id,
            "numero_acta": self.numero_acta,
            "anio": self.anio,
            "mes": self.mes,
            "motivo": self.motivo,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
            "sin_expediente_envio": self.sin_expediente_envio,
            "sin_expediente_envio_declarado_at": self.sin_expediente_envio_declarado_at,
            "sin_expediente_envio_declarado_by_user_id": self.sin_expediente_envio_declarado_by_user_id,
        }

        if include_relations:
            data["actuacion"] = self.actuaciones.to_dict() if self.actuaciones else None

            oficios = []
            if self.oficio:
                for o in self.oficio:
                    oficios.append(o.to_dict())
            data["oficios"] = oficios

            expedientes = []
            if self.expediente:
                for e in self.expediente:
                    expedientes.append(e.to_dict())
            data["expedientes"] = expedientes

        return data
