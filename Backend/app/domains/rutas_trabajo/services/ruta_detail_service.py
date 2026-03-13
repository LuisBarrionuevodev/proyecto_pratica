from __future__ import annotations

from app.models import RutaGrupo, RutaTrabajo


def get_ruta_detail_min(ruta_id: int) -> tuple[RutaTrabajo, list[RutaGrupo]]:
    """
    Obtiene detalle mínimo de ruta para PR2.

    Incluye:
    - RutaTrabajo
    - grupos no soft-deleted
    - inspectores por grupo (via relationship)

    Errores:
    - LookupError: cuando la ruta no existe.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")

    grupos = (
        RutaGrupo.query.filter(
            RutaGrupo.ruta_trabajo_id == ruta.id,
            RutaGrupo.deleted_at.is_(None),
        )
        .order_by(RutaGrupo.id.asc())
        .all()
    )
    return ruta, grupos
