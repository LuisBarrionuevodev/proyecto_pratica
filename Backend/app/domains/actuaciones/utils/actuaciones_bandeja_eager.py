"""Eager-load de relaciones usadas por presenters de bandejas documentales."""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import joinedload, selectinload

from app.models import Actuaciones, Domicilio, Notificacion


def options_actuacion_bandeja_grid() -> tuple:
    """
    Opciones ORM para ``actuacion_to_grid_row`` y filas derivadas (expediente / oficio).

    - ``joinedload`` en relaciones many-to-one / one-to-one.
    - ``selectinload`` en colecciones (inspectores, motivos de notificación).
    """
    return (
        joinedload(Actuaciones.orden_trabajo),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
        joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
        selectinload(Actuaciones.inspector),
        joinedload(Actuaciones.inspeccion),
        joinedload(Actuaciones.clausura),
        joinedload(Actuaciones.decomiso),
        joinedload(Actuaciones.notificacion).selectinload(Notificacion.motivos),
        joinedload(Actuaciones.comprobacion),
    )


def apply_bandeja_grid_eager(query):
    """
    Aplica eager-load de bandeja a un query de ``Actuaciones``.

    Parámetros:
        query: query SQLAlchemy sobre ``Actuaciones``.

    Retorno:
        Query con ``options()`` aplicadas.
    """
    return query.options(*options_actuacion_bandeja_grid())


def reload_actuaciones_bandeja_eager(acts: List[Actuaciones]) -> List[Actuaciones]:
    """
    Re-carga actuaciones por id con eager-load, conservando el orden de entrada.

    Útil cuando el fetch inicial no admite ``options()`` (p. ej. ``union``).

    Parámetros:
        acts: filas ya resueltas (solo se usan los ids).

    Retorno:
        Mismas actuaciones con relaciones precargadas, en el mismo orden.
    """
    if not acts:
        return acts
    ids = [int(a.id) for a in acts]
    order_index = {aid: idx for idx, aid in enumerate(ids)}
    rows = (
        Actuaciones.query.filter(Actuaciones.id.in_(ids))
        .options(*options_actuacion_bandeja_grid())
        .all()
    )
    rows.sort(key=lambda a: order_index.get(int(a.id), 0))
    return rows
