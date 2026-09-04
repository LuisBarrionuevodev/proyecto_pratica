"""
Criterio compartido: actuación base de nueva inspección para workflow documental.

Usado por sync/listados de notificación vencida sin mutar ``Actuaciones.tipo``.
"""

from __future__ import annotations

from sqlalchemy import and_, or_

from app.models import Actuaciones

TIPO_INSPECCION = "INSPECCION"
TIPO_VERIFICAR_INFORMAR = "VERIFICAR E INFORMAR"


def actuacion_equivale_a_inspeccion_para_workflow_documental(act: Actuaciones) -> bool:
    """
    True si la actuación cuenta como inspección real para canales NOTIFICACION/COMPROBACION.

    Parámetros:
        act: fila ``Actuaciones`` (en memoria o persistida).

    Retorno:
        True para ``INSPECCION`` o ``VERIFICAR E INFORMAR`` con ``realizo_nueva_inspeccion`` explícito True.
    """
    tipo = getattr(act, "tipo", None)
    if tipo == TIPO_INSPECCION:
        return True
    if tipo == TIPO_VERIFICAR_INFORMAR:
        return act.realizo_nueva_inspeccion is True
    return False


def filtro_sql_actuacion_base_workflow_documental():
    """
    Expresión SQLAlchemy equivalente a ``actuacion_equivale_a_inspeccion_para_workflow_documental``.

    Retorno:
        ``or_(...)`` aplicable en ``.filter()`` sobre ``Actuaciones``.
    """
    return or_(
        Actuaciones.tipo == TIPO_INSPECCION,
        and_(
            Actuaciones.tipo == TIPO_VERIFICAR_INFORMAR,
            Actuaciones.realizo_nueva_inspeccion.is_(True),
        ),
    )
