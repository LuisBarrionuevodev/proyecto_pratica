from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from app.models import Notificacion

DEFAULT_PLAZO_DIAS = 5


def calcular_fecha_vencimiento(
    fecha_notificacion: date,
    plazo_dias: int,
    prorroga_dias: int,
) -> date:
    """
    Calcula fecha de vencimiento de notificación.

    Regla:
    - fecha_vencimiento = fecha_notificacion + plazo_dias + prorroga_dias
    """
    total_dias = max(0, int(plazo_dias)) + max(0, int(prorroga_dias))
    return fecha_notificacion + timedelta(days=total_dias)


def inicializar_timing_notificacion(
    notificacion: Notificacion,
    *,
    fecha_notificacion: Optional[date],
) -> None:
    """
    Inicializa campos de timing de notificación con defaults de negocio.

    - plazo_dias por defecto 5
    - prorroga_dias por defecto 0
    - fecha_notificacion desde actuación
    - fecha_vencimiento calculada
    """
    if notificacion.plazo_dias is None:
        notificacion.plazo_dias = DEFAULT_PLAZO_DIAS
    if notificacion.prorroga_dias is None:
        notificacion.prorroga_dias = 0
    if notificacion.fecha_notificacion is None and fecha_notificacion is not None:
        notificacion.fecha_notificacion = fecha_notificacion
    if notificacion.fecha_notificacion is not None:
        notificacion.fecha_vencimiento = calcular_fecha_vencimiento(
            notificacion.fecha_notificacion,
            notificacion.plazo_dias,
            notificacion.prorroga_dias,
        )


def aplicar_prorroga_notificacion(notificacion: Notificacion, prorroga_dias_solicitada: int) -> None:
    """
    Aplica prórroga en forma acumulativa y recalcula vencimiento.

    Raises:
        ValueError: si prorroga_dias_solicitada es negativa o falta fecha base.
    """
    if prorroga_dias_solicitada is None:
        raise ValueError("prorroga_dias es obligatorio para NOTIFICACION")
    if int(prorroga_dias_solicitada) < 0:
        raise ValueError("prorroga_dias debe ser mayor o igual a 0")
    if notificacion.fecha_notificacion is None:
        raise ValueError("La notificación no tiene fecha_notificacion para recalcular vencimiento")

    notificacion.plazo_dias = notificacion.plazo_dias if notificacion.plazo_dias is not None else DEFAULT_PLAZO_DIAS
    notificacion.prorroga_dias = (notificacion.prorroga_dias or 0) + int(prorroga_dias_solicitada)
    notificacion.fecha_vencimiento = calcular_fecha_vencimiento(
        notificacion.fecha_notificacion,
        notificacion.plazo_dias,
        notificacion.prorroga_dias,
    )
