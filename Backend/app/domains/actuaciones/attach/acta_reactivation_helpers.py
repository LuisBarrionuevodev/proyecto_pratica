"""
Helpers para reutilizar actas soft-deleted al re-vincular desde Actuaciones CRUD.
"""

from __future__ import annotations

from app.models import Actuaciones


def otra_actuacion_usa_notificacion(notificacion_id: int, excluir_actuacion_id: int) -> bool:
    """
    True si otra actuación distinta ya referencia la notificación.

    Parámetros:
        notificacion_id: PK de ``Notificacion``.
        excluir_actuacion_id: actuación que está editando (se excluye del chequeo).

    Retorno:
        ``True`` si hay conflicto de vínculo activo.
    """
    return (
        Actuaciones.query.filter(
            Actuaciones.notificacion_id == int(notificacion_id),
            Actuaciones.id != int(excluir_actuacion_id),
        ).first()
        is not None
    )


def otra_actuacion_usa_comprobacion(comprobacion_id: int, excluir_actuacion_id: int) -> bool:
    """
    True si otra actuación distinta ya referencia la comprobación.

    Parámetros:
        comprobacion_id: PK de ``Comprobacion``.
        excluir_actuacion_id: actuación que está editando.

    Retorno:
        ``True`` si hay conflicto de vínculo activo.
    """
    return (
        Actuaciones.query.filter(
            Actuaciones.comprobacion_id == int(comprobacion_id),
            Actuaciones.id != int(excluir_actuacion_id),
        ).first()
        is not None
    )
