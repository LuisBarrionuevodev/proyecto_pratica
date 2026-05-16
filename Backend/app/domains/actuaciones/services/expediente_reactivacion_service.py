"""
Reactivación controlada de expedientes soft-deleted en el **mismo** circuito documental.

Solo se reutiliza la fila cuando coinciden número, año y anclaje (comprobación / oficio / notificación)
y tipo de etapa; no se reactivan expedientes de otro circuito aunque compartan número/año.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import or_

from app.models import Expediente


def buscar_expediente_envio_comprobacion_reactivable(
    *,
    comprobacion_id: int,
    numero_expediente: str,
    anio: str,
) -> Optional[Expediente]:
    """
    Expediente de envío de acta (``ENVIO_ACTA``) borrado en soft delete, mismo ``comprobacion_id``
    y sin vínculo a oficio ni notificación.

    Parámetros:
        comprobacion_id: comprobación del circuito.
        numero_expediente: número normalizado (6 caracteres).
        anio: año contable como string (4 dígitos).

    Retorno:
        La fila más antigua que cumple, o ``None``.
    """
    return (
        Expediente.query.filter(
            Expediente.comprobacion_id == int(comprobacion_id),
            Expediente.oficio_id.is_(None),
            Expediente.notificacion_id.is_(None),
            or_(
                Expediente.tipo_expediente == "ENVIO_ACTA",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.numero_expediente == numero_expediente,
            Expediente.anio == anio,
            Expediente.deleted_at.isnot(None),
        )
        .order_by(Expediente.id.asc())
        .first()
    )


def buscar_expediente_respuesta_oficio_reactivable(
    *,
    comprobacion_id: int,
    oficio_id: int,
    numero_expediente: str,
    anio: str,
) -> Optional[Expediente]:
    """
    Expediente ``RESPUESTA_OFICIO`` soft-deleted para el mismo oficio y comprobación.

    Parámetros:
        comprobacion_id: comprobación del contexto.
        oficio_id: oficio al que responde el expediente.
        numero_expediente: número normalizado.
        anio: año como string.

    Retorno:
        La fila más reciente que cumple (último borrado del bloque), o ``None``.
    """
    return (
        Expediente.query.filter(
            Expediente.comprobacion_id == int(comprobacion_id),
            Expediente.oficio_id == int(oficio_id),
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.numero_expediente == numero_expediente,
            Expediente.anio == anio,
            Expediente.deleted_at.isnot(None),
        )
        .order_by(Expediente.id.desc())
        .first()
    )


def buscar_expediente_prorroga_notificacion_reactivable(
    *,
    notificacion_id: int,
    numero_expediente: str,
    anio: str,
) -> Optional[Expediente]:
    """
    Expediente ``PRORROGA_NOTIFICACION`` soft-deleted para la misma notificación.

    Parámetros:
        notificacion_id: notificación del circuito.
        numero_expediente: número normalizado.
        anio: año como string.

    Retorno:
        La fila más antigua que cumple, o ``None``.
    """
    return (
        Expediente.query.filter(
            Expediente.notificacion_id == int(notificacion_id),
            Expediente.comprobacion_id.is_(None),
            Expediente.oficio_id.is_(None),
            or_(
                Expediente.tipo_expediente == "PRORROGA_NOTIFICACION",
                Expediente.tipo_expediente.is_(None),
            ),
            Expediente.numero_expediente == numero_expediente,
            Expediente.anio == anio,
            Expediente.deleted_at.isnot(None),
        )
        .order_by(Expediente.id.asc())
        .first()
    )


def aplicar_reactivacion_envio_comprobacion(
    ex: Expediente,
    *,
    fecha_expediente: date,
    anio_str: str,
) -> None:
    """
    Marca el expediente como activo y actualiza fecha/año contable.

    No hace commit.
    """
    ex.deleted_at = None
    ex.fecha_expediente = fecha_expediente
    ex.anio = anio_str
    ex.tipo_expediente = "ENVIO_ACTA"


def aplicar_reactivacion_respuesta_oficio(
    ex: Expediente,
    *,
    fecha_expediente: date,
    anio_str: str,
) -> None:
    """Reactiva expediente de respuesta y alinea fecha/año. No hace commit."""
    ex.deleted_at = None
    ex.fecha_expediente = fecha_expediente
    ex.anio = anio_str
    ex.tipo_expediente = "RESPUESTA_OFICIO"


def aplicar_reactivacion_prorroga(
    ex: Expediente,
    *,
    fecha_expediente: date,
    anio_str: str,
    prorroga_dias_otorgados: int,
) -> None:
    """Reactiva expediente de prórroga y actualiza plazo documental. No hace commit."""
    ex.deleted_at = None
    ex.fecha_expediente = fecha_expediente
    ex.anio = anio_str
    ex.prorroga_dias_otorgados = int(prorroga_dias_otorgados)
    ex.tipo_expediente = "PRORROGA_NOTIFICACION"
