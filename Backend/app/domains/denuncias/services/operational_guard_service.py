from __future__ import annotations

from app.models import IniciadorRuta


class DenunciaNoOperativaError(ValueError):
    """Error de negocio para denuncias fuera de gestión operativa."""


def get_iniciador_pendiente_denuncia(denuncia_id: int) -> IniciadorRuta:
    """
    Retorna el iniciador pendiente activo de la denuncia.

    Regla operativa:
    - tipo_iniciador = DENUNCIA
    - estado_iniciador = PENDIENTE
    - deleted_at IS NULL
    """
    iniciador = (
        IniciadorRuta.query.filter(
            IniciadorRuta.denuncia_id == denuncia_id,
            IniciadorRuta.tipo_iniciador == "DENUNCIA",
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if not iniciador:
        raise DenunciaNoOperativaError(
            "La denuncia ya no está operativa (sin iniciador pendiente) y no puede editarse/eliminarse."
        )
    return iniciador
