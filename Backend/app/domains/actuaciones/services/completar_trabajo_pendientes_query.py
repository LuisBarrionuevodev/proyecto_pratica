from __future__ import annotations

from sqlalchemy.orm import joinedload, selectinload

from app.domains.usuarios.services.inspector_query_scope import scope_ruta_items_to_inspector
from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo


def completar_trabajo_pendientes_ruta_item_base_query():
    """
    Query base de ítems en ámbito Completar trabajo (ruta PUBLICADA, con actuación mínima).

    Retorno:
        Consulta sobre ``RutaItem`` con eager loads del listado/detalle.
    """
    return (
        RutaItem.query.join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
        )
        .options(
            joinedload(RutaItem.actuacion).options(
                joinedload(Actuaciones.orden_trabajo),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
                selectinload(Actuaciones.inspector),
            ),
            joinedload(RutaItem.iniciador_ruta).options(
                joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
                joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
                joinedload(IniciadorRuta.notificacion),
            ),
            joinedload(RutaItem.ruta_grupo)
            .selectinload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
    )


def apply_completar_trabajo_inspector_scope(query, inspector_id: int | None):
    """
    Aplica scope por Inspector al query de ``RutaItem`` (sin efecto si ``inspector_id`` es None).

    Parámetros:
        query: consulta base de Completar trabajo.
        inspector_id: id efectivo del Inspector autenticado.

    Retorno:
        Query restringido o sin cambios para admin/usuario.
    """
    if inspector_id is None:
        return query
    return scope_ruta_items_to_inspector(query, int(inspector_id))
