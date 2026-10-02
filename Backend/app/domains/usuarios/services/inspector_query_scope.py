from __future__ import annotations

from sqlalchemy import and_, exists

from app.models import Actuaciones, RutaGrupo, RutaItem
from app.models.actuaciones_inspector import actuaciones_inspector
from app.models.ruta_grupo_inspector import RutaGrupoInspector


def scope_ruta_items_to_inspector(query, inspector_id: int):
    """
    Restringe un query de ``RutaItem`` a ítems cuyo grupo incluye al Inspector.

    Cadena: ``RutaItem`` → ``RutaGrupo`` → ``RutaGrupoInspector`` → ``inspector_id``.

    Parámetros:
        query: consulta SQLAlchemy sobre ``RutaItem``.
        inspector_id: inspector operativo efectivo.

    Retorno:
        Query filtrado (excluye ítems/grupos soft-deleted).
    """
    iid = int(inspector_id)
    return query.filter(
        RutaItem.deleted_at.is_(None),
        RutaItem.ruta_grupo_id.isnot(None),
        exists().where(
            and_(
                RutaGrupo.id == RutaItem.ruta_grupo_id,
                RutaGrupo.deleted_at.is_(None),
                RutaGrupoInspector.ruta_grupo_id == RutaGrupo.id,
                RutaGrupoInspector.inspector_id == iid,
            )
        ),
    )


def scope_actuaciones_to_inspector(query, inspector_id: int):
    """
    Restringe un query de ``Actuaciones`` a filas vinculadas en ``actuaciones_inspector``.

    Parámetros:
        query: consulta SQLAlchemy sobre ``Actuaciones``.
        inspector_id: inspector operativo efectivo.

    Retorno:
        Query filtrado (excluye vínculos soft-deleted).
    """
    iid = int(inspector_id)
    return query.filter(
        exists().where(
            and_(
                actuaciones_inspector.c.actuaciones_id == Actuaciones.id,
                actuaciones_inspector.c.inspector_id == iid,
                actuaciones_inspector.c.deleted_at.is_(None),
            )
        )
    )
