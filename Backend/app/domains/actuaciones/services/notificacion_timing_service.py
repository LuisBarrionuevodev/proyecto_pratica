from __future__ import annotations

from datetime import date
from typing import Optional, Sequence, Union

from app.models import Notificacion
from app.shared.utils.business_days_ar import (
    calcular_fecha_vencimiento_notificacion_habiles,
    sumar_dias_habiles_posteriores_a_fecha,
)

DEFAULT_PLAZO_DIAS = 5

FechaExpedienteInput = Union[date, None]


def _coerce_fecha_expediente(fecha_expediente: date) -> date:
    """Asegura ``date`` puro (sin componente horario)."""
    from datetime import datetime as dt

    if isinstance(fecha_expediente, dt):
        return fecha_expediente.date()
    return fecha_expediente


def calcular_fecha_vencimiento_desde_expediente_prorroga(
    fecha_expediente: date,
    plazo_otorgado: int,
) -> date:
    """
    Vencimiento cuando la notificación **ya estaba vencida** al expediente: ``plazo_otorgado``
    días hábiles desde ``fecha_expediente`` (día del expediente no cuenta).

    No usar si todavía había plazo vigente; en ese caso acumular sobre ``fecha_vencimiento``.
    """
    base = _coerce_fecha_expediente(fecha_expediente)
    return calcular_fecha_vencimiento_notificacion_habiles(
        base,
        max(0, int(plazo_otorgado)),
    )


def aplicar_prorroga_a_vencimiento_acumulado(
    vencimiento_actual: date,
    fecha_expediente: date,
    plazo_otorgado: int,
) -> date:
    """
    Aplica una fila de prórroga sobre el vencimiento acumulado previo.

    Reglas:
    - Si ``vencimiento_actual >= fecha_expediente`` (aún había plazo al expediente):
      suma ``plazo_otorgado`` hábiles al vencimiento vigente.
    - Si ya estaba vencida para la fecha del expediente:
      ``fecha_expediente + plazo_otorgado`` (días hábiles AR).

    Parámetros:
        vencimiento_actual: vencimiento tras plazo inicial o prórrogas anteriores.
        fecha_expediente: fecha del expediente ``PRORROGA_NOTIFICACION``.
        plazo_otorgado: días hábiles otorgados en ese expediente.

    Retorno:
        Nuevo vencimiento operativo.
    """
    plazo = max(0, int(plazo_otorgado))
    if plazo <= 0:
        return vencimiento_actual
    fexp = _coerce_fecha_expediente(fecha_expediente)
    if vencimiento_actual >= fexp:
        return sumar_dias_habiles_posteriores_a_fecha(vencimiento_actual, plazo)
    return calcular_fecha_vencimiento_desde_expediente_prorroga(fexp, plazo)


def calcular_vencimiento_notificacion_con_prorrogas(
    fecha_notificacion: date,
    plazo_dias: int,
    expedientes: Sequence[tuple[date, int]],
) -> date:
    """
    Vencimiento final: plazo legal inicial + cadena de prórrogas activas en orden cronológico.

    Parámetros:
        fecha_notificacion: fecha de la acta de notificación.
        plazo_dias: plazo legal inicial en días hábiles.
        expedientes: secuencia ``(fecha_expediente, plazo_otorgado)`` ordenada ASC por
            ``fecha_expediente`` y ``id``.

    Retorno:
        ``fecha_vencimiento`` operativa consolidada.
    """
    vencimiento = calcular_fecha_vencimiento(fecha_notificacion, plazo_dias, 0)
    for fecha_exp, plazo in expedientes:
        vencimiento = aplicar_prorroga_a_vencimiento_acumulado(vencimiento, fecha_exp, plazo)
    return vencimiento


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
    .. deprecated::
        No usar en flujos nuevos. El vencimiento con prórroga se recalcula vía
        ``recalcular_vencimiento_notificacion_desde_expedientes`` (cadena acumulada de prórrogas).

    Aplica prórroga en forma acumulativa desde ``fecha_notificacion`` (legado).

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
