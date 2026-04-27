"""
Edición controlada del expediente de prórroga ligado a una notificación (rama NOTIFICACION).

Regla de negocio:
- Mientras la notificación **no** haya sido usada como iniciador (``IniciadorRuta`` no borrado con
  ``notificacion_id``), se puede editar cada expediente ``PRORROGA_NOTIFICACION`` (número, fecha,
  plazo otorgado en días).
- Con al menos un iniciador vinculado, la edición queda bloqueada.

Al guardar se actualiza la fila ``expediente``, se recalcula ``Notificacion.prorroga_dias`` como la
suma de ``prorroga_dias_otorgados`` de todas las prórrogas de esa notificación y se recalcula
``fecha_vencimiento`` (días hábiles AR).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

from app.database import db
from app.models import Actuaciones, Expediente, IniciadorRuta, Notificacion
from app.utils.actas import acta_6
from app.domains.actuaciones.services.notificacion_timing_service import (
    DEFAULT_PLAZO_DIAS,
    calcular_fecha_vencimiento,
)


def notificacion_usada_como_iniciador(notificacion_id: int) -> bool:
    """
    Indica si la notificación ya figura como iniciador materializado en rutas.

    Criterio: existe al menos una fila ``IniciadorRuta`` con ``notificacion_id`` igual a esta
    notificación y ``deleted_at`` nulo.

    Parámetros:
        notificacion_id: PK de ``notificacion``.

    Retorno:
        True si hay al menos un iniciador activo vinculado.

    Errores:
        Ninguno (consulta de solo lectura).
    """
    return (
        db.session.query(IniciadorRuta.id)
        .filter(
            IniciadorRuta.notificacion_id == int(notificacion_id),
            IniciadorRuta.deleted_at.is_(None),
        )
        .limit(1)
        .first()
        is not None
    )


_MSG_BLOQUEO_USADA = (
    "Esta notificación ya fue usada como iniciador en el plan de rutas "
    "(existe al menos un registro en iniciador_ruta vinculado a esta notificación). "
    "No se pueden editar los expedientes de prórroga."
)


def evaluar_notificacion_edicion_permisos(act: Actuaciones) -> Dict[str, Any]:
    """
    Evalúa si se pueden editar expedientes ``PRORROGA_NOTIFICACION`` de la notificación de la actuación.

    Parámetros:
        act: actuación con ``notificacion_id`` (rama gestión notificación).

    Retorno:
        dict con ``puede_editar_expediente_prorroga``, ``notificacion_usada_como_iniciador`` y
        ``motivos_bloqueo_expediente``.

    Errores:
        Ninguno (solo lectura).
    """
    motivos: List[str] = []

    if act.notificacion_id is None:
        motivos.append("La actuación no tiene notificación asociada.")
        return {
            "puede_editar_expediente_prorroga": False,
            "notificacion_usada_como_iniciador": False,
            "motivos_bloqueo_expediente": motivos,
        }

    nid = int(act.notificacion_id)
    usada = notificacion_usada_como_iniciador(nid)
    if usada:
        motivos.append(_MSG_BLOQUEO_USADA)

    puede = not usada
    return {
        "puede_editar_expediente_prorroga": puede,
        "notificacion_usada_como_iniciador": usada,
        "motivos_bloqueo_expediente": motivos,
    }


def _resolver_notificacion_y_expediente_prorroga(
    actuacion_id: int, expediente_id: int
) -> Tuple[Actuaciones, Notificacion, Expediente]:
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.notificacion_id is None:
        raise ValueError("La actuación no tiene notificación asociada")

    noti = db.session.get(Notificacion, int(act.notificacion_id))
    if noti is None:
        raise ValueError("Notificación no encontrada para la actuación")

    ex = db.session.get(Expediente, expediente_id)
    if ex is None or ex.deleted_at is not None:
        raise LookupError("Expediente no encontrado")
    if ex.notificacion_id != int(noti.id):
        raise ValueError("El expediente no pertenece a la notificación de esta actuación")
    if ex.tipo_expediente != "PRORROGA_NOTIFICACION":
        raise ValueError("Solo se pueden editar expedientes de tipo prórroga de notificación")

    return act, noti, ex


def _recalcular_prorroga_y_vencimiento(noti: Notificacion) -> None:
    """
    Asigna ``Notificacion.prorroga_dias`` como suma de ``prorroga_dias_otorgados`` de prórrogas
    activas y recalcula ``fecha_vencimiento``.

    Parámetros:
        noti: notificación con ``fecha_notificacion`` definida para el cálculo.

    Retorno:
        None (muta ``noti``).

    Errores:
        ValueError: si falta ``fecha_notificacion``.
    """
    if noti.fecha_notificacion is None:
        raise ValueError("La notificación no tiene fecha_notificacion para recalcular vencimiento")

    rows: List[Expediente] = (
        Expediente.query.filter_by(notificacion_id=noti.id)
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .all()
    )
    total = sum(int(r.prorroga_dias_otorgados or 0) for r in rows)
    noti.prorroga_dias = total
    noti.plazo_dias = noti.plazo_dias if noti.plazo_dias is not None else DEFAULT_PLAZO_DIAS
    noti.fecha_vencimiento = calcular_fecha_vencimiento(
        noti.fecha_notificacion,
        noti.plazo_dias,
        noti.prorroga_dias or 0,
    )
    db.session.add(noti)


def update_notificacion_prorroga_expediente(
    actuacion_id: int,
    expediente_id: int,
    *,
    numero_expediente: str,
    fecha_expediente: date,
    plazo_otorgado: int,
) -> Dict[str, Any]:
    """
    Actualiza número, fecha y plazo otorgado (días) de un expediente ``PRORROGA_NOTIFICACION``.

    Persiste ``prorroga_dias_otorgados`` en la fila, recalcula la suma en ``Notificacion.prorroga_dias``
    y ``fecha_vencimiento``.

    Parámetros:
        actuacion_id: PK de la actuación (contexto de permisos y notificación).
        expediente_id: PK del expediente a corregir.
        numero_expediente: número normalizado (6 dígitos vía ``acta_6``).
        fecha_expediente: fecha del expediente (define año contable).
        plazo_otorgado: días de prórroga otorgados en esta fila (>= 0).

    Retorno:
        dict con ``expediente`` (ORM) e ``item`` serializable mínimo.

    Errores:
        LookupError: 404 actuación o expediente.
        ValueError: 400 reglas de negocio o payload.
        RuntimeError: 409 conflicto de unicidad (número/año ya existe en otro expediente).
    """
    act, noti, ex = _resolver_notificacion_y_expediente_prorroga(actuacion_id, expediente_id)

    per = evaluar_notificacion_edicion_permisos(act)
    if not per["puede_editar_expediente_prorroga"]:
        raise ValueError(
            per["motivos_bloqueo_expediente"][0] if per["motivos_bloqueo_expediente"] else "Edición no permitida"
        )

    if int(plazo_otorgado) < 0:
        raise ValueError("plazo_otorgado debe ser mayor o igual a 0")

    num = acta_6(numero_expediente)
    if not num:
        raise ValueError("numero_expediente inválido")
    anio_str = str(fecha_expediente.year)

    dup = (
        Expediente.query.filter(Expediente.numero_expediente == num, Expediente.anio == anio_str)
        .filter(Expediente.id != ex.id)
        .filter(Expediente.deleted_at.is_(None))
        .first()
    )
    if dup:
        raise RuntimeError("Ya existe otro expediente con ese número y año")

    ex.numero_expediente = num
    ex.fecha_expediente = fecha_expediente
    ex.anio = anio_str
    ex.prorroga_dias_otorgados = int(plazo_otorgado)
    db.session.add(ex)

    _recalcular_prorroga_y_vencimiento(noti)
    db.session.commit()

    return {
        "expediente": ex,
        "notificacion": noti,
        "item": {
            "id": ex.id,
            "numero_expediente": ex.numero_expediente,
            "anio": ex.anio,
            "fecha_expediente": ex.fecha_expediente.isoformat() if ex.fecha_expediente else None,
            "tipo_expediente": ex.tipo_expediente,
            "plazo_otorgado": ex.prorroga_dias_otorgados,
        },
    }
