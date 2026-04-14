from __future__ import annotations

from datetime import date
from typing import Optional

from app.models import Notificacion
from app.shared.utils.business_days_ar import calcular_fecha_vencimiento_notificacion_habiles

DEFAULT_PLAZO_DIAS = 5


def calcular_fecha_vencimiento(
    fecha_notificacion: date,
    plazo_dias: int,
    prorroga_dias: int,
) -> date:
    """
    Calcula fecha de vencimiento de notificación en **días hábiles** (AR).

    Regla:
    - El día de ``fecha_notificacion`` no cuenta.
    - El plazo empieza el próximo día hábil posterior.
    - ``plazo_dias`` y ``prorroga_dias`` se suman como total de días hábiles del plazo (inclusive inicio).
    - No son hábiles: sábado, domingo y feriados nacionales (ver ``feriados_nacionales_ar``).
    """
    total_habiles = max(0, int(plazo_dias)) + max(0, int(prorroga_dias))
    return calcular_fecha_vencimiento_notificacion_habiles(fecha_notificacion, total_habiles)


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
