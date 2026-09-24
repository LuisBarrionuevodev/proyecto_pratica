import enum

from app.database import db


class EstadoEventoParticipante(enum.Enum):
    NO_RINDIO = "NO_RINDIO"
    APROBADO = "APROBADO"
    DESAPROBADO = "DESAPROBADO"
    INSCRIPTO = "INSCRIPTO"
    ASISTIO = "ASISTIO"
    AUSENTE = "AUSENTE"
    RINDIO = "RINDIO"


class EventoParticipante(db.Model):
    __tablename__ = "evento_participante"

    evento_id = db.Column(
        db.Integer,
        db.ForeignKey("eventos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    participante_id = db.Column(
        db.Integer,
        db.ForeignKey("participantes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nota = db.Column(db.Numeric(5, 2), nullable=True)
    estado = db.Column(
        db.Enum(EstadoEventoParticipante, name="estado_evento_participante"),
        nullable=False,
        server_default=EstadoEventoParticipante.NO_RINDIO.value,
    )

    evento = db.relationship("Evento")
    participante = db.relationship("Participante")

    def to_dict(self):
        return {
            "evento_id": self.evento_id,
            "participante_id": self.participante_id,
            "nota": str(self.nota) if self.nota is not None else None,
            "estado": self.estado.value if self.estado else None,
        }
