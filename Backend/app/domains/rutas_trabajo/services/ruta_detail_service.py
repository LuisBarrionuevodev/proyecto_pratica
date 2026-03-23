from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Domicilio,
    IniciadorRuta,
    Relevamiento,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
    RutaTrabajo,
)


def get_ruta_detail_min(ruta_id: int) -> tuple[RutaTrabajo, list[RutaGrupo]]:
    """
    Obtiene detalle mínimo de ruta para PR2.

    Incluye:
    - RutaTrabajo
    - grupos no soft-deleted
    - inspectores por grupo (via relationship)
    - eager load de ítems → iniciador → domicilio (geocode, distrito, rubro) para payload mapa sin N+1

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
        .options(
            selectinload(RutaGrupo.grupo_inspectores).joinedload(RutaGrupoInspector.inspector),
            selectinload(RutaGrupo.items).options(
                joinedload(RutaItem.orden_trabajo),
                joinedload(RutaItem.iniciador_ruta).options(
                    joinedload(IniciadorRuta.domicilio).options(
                        joinedload(Domicilio.geocode),
                        joinedload(Domicilio.distrito),
                        joinedload(Domicilio.rubro),
                        joinedload(Domicilio.calle_catalogo),
                    ),
                    joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
                ),
            ),
        )
        .all()
    )
    return ruta, grupos
