"""
Filtros SQL para KPIs de notificación labrada (excluye FK referencial de origen).

Semántica alineada a ``notificacion_es_origen_reinspeccion_notificacion_en_actuacion``
en ``oficio_circuito_service.py``.
"""

from __future__ import annotations

from sqlalchemy import exists

from app.models import Actuaciones, IniciadorRuta, RutaItem


def notificacion_origen_reinspeccion_referencial_exists():
    """
    EXISTS: ``act.notificacion_id`` es la notificación de origen del iniciador
    ``REINSPECCION_NOTIFICACION`` del cierre (referencia operativa, no acta labrada).

    Retorno:
        Expresión SQLAlchemy para usar con ``~`` o ``not_()`` en filtros de KPI.
    """
    return (
        exists()
        .where(
            RutaItem.actuacion_id == Actuaciones.id,
            RutaItem.deleted_at.is_(None),
            IniciadorRuta.id == RutaItem.iniciador_ruta_id,
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.notificacion_id.isnot(None),
            IniciadorRuta.notificacion_id == Actuaciones.notificacion_id,
        )
        .correlate(Actuaciones)
    )
