from __future__ import annotations

from app.models import IniciadorRuta


class RelevamientoNoOperativoError(ValueError):
    """Error de negocio para relevamientos fuera de gestión operativa."""


def get_iniciador_pendiente_relevamiento(relevamiento_id: int) -> IniciadorRuta:
    """
    Retorna el iniciador pendiente activo del relevamiento.

    Regla operativa:
    - tipo_iniciador = RELEVAMIENTO
    - estado_iniciador = PENDIENTE
    - deleted_at IS NULL
    """
    iniciador = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == relevamiento_id,
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if not iniciador:
        raise RelevamientoNoOperativoError(
            "El relevamiento ya no está operativo (sin iniciador pendiente) y no puede editarse/eliminarse."
        )
    return iniciador
