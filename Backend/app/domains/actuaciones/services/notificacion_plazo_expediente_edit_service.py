"""
Edición y eliminación controladas del expediente de prórroga ligado a una notificación (rama NOTIFICACION).

Regla de negocio:
- Solo el **último** expediente ``PRORROGA_NOTIFICACION`` activo puede editarse o eliminarse.
- Bloqueo por uso operativo real de la reinspección (iniciador CUMPLIDO, ruta REALIZADA, acta REINSPECCION),
  no por la mera existencia de un ``IniciadorRuta`` en PENDIENTE o ANULADO.
- Al guardar o eliminar se recalcula vencimiento vía motor único de prórrogas.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import aliased

from app.database import db
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    revoke_reinspeccion_notificacion_iniciadores_obsoletos,
)
from app.models import Actuaciones, Expediente, IniciadorRuta, Notificacion, RutaItem
from app.utils.actas import acta_6
from app.domains.actuaciones.services.notificacion_timing_service import (
    DEFAULT_PLAZO_DIAS,
    aplicar_prorroga_a_vencimiento_acumulado,
    calcular_fecha_vencimiento,
)

logger = logging.getLogger(__name__)

_MSG_BLOQUEO_USADA = (
    "Este expediente de prórroga ya fue utilizado en una reinspección completada "
    "y no puede modificarse desde esta vista."
)
_MSG_BLOQUEO_NO_ULTIMO = "Solo se puede modificar el último expediente de prórroga."


def _as_fecha_expediente_operativa(value: date | datetime | None) -> date | None:
    """
    Normaliza ``fecha_expediente`` a ``date`` (nunca ``created_at`` / ``updated_at``).

    Parámetros:
        value: valor ORM (``date`` o ``datetime``).

    Retorno:
        ``date`` o ``None``.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def notificacion_tiene_reinspeccion_operativamente_usada(notificacion_id: int) -> bool:
    """
    Indica si la reinspección por notificación ya fue usada operativamente.

    Devuelve True solo si existe evidencia de cierre real (no basta con iniciador PENDIENTE/ANULADO):
    - iniciador ``REINSPECCION_NOTIFICACION`` en ``CUMPLIDO``;
    - ``RutaItem`` ``FINALIZADO`` + ``REALIZADO`` del iniciador;
    - actuación ``REINSPECCION`` con el mismo ``notificacion_id``;
    - ``RutaItem`` con actuación ``REINSPECCION`` vinculada al iniciador (reinspección huérfana).

    Parámetros:
        notificacion_id: PK de ``notificacion``.

    Retorno:
        True si la reinspección ya fue completada operativamente.

    Errores:
        Ninguno (consulta de solo lectura).
    """
    nid = int(notificacion_id)

    if (
        db.session.query(IniciadorRuta.id)
        .filter(
            IniciadorRuta.notificacion_id == nid,
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            IniciadorRuta.estado_iniciador == "CUMPLIDO",
        )
        .limit(1)
        .first()
        is not None
    ):
        return True

    if (
        db.session.query(RutaItem.id)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .filter(
            IniciadorRuta.notificacion_id == nid,
            IniciadorRuta.deleted_at.is_(None),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
            RutaItem.estado_ejecucion == "REALIZADO",
        )
        .limit(1)
        .first()
        is not None
    ):
        return True

    if (
        db.session.query(Actuaciones.id)
        .filter(
            Actuaciones.notificacion_id == nid,
            Actuaciones.tipo == "REINSPECCION",
        )
        .limit(1)
        .first()
        is not None
    ):
        return True

    A_rein = aliased(Actuaciones)
    return (
        db.session.query(RutaItem.id)
        .join(IniciadorRuta, RutaItem.iniciador_ruta_id == IniciadorRuta.id)
        .join(A_rein, RutaItem.actuacion_id == A_rein.id)
        .filter(
            IniciadorRuta.notificacion_id == nid,
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.tipo_iniciador == "REINSPECCION_NOTIFICACION",
            RutaItem.deleted_at.is_(None),
            RutaItem.actuacion_id.isnot(None),
            A_rein.tipo == "REINSPECCION",
        )
        .limit(1)
        .first()
        is not None
    )


def notificacion_usada_como_iniciador(notificacion_id: int) -> bool:
    """
    Alias de compatibilidad API: uso operativo real de reinspección (no mera existencia de iniciador).

    Ver ``notificacion_tiene_reinspeccion_operativamente_usada``.
    """
    return notificacion_tiene_reinspeccion_operativamente_usada(notificacion_id)


def _ultimo_expediente_prorroga_activo(notificacion_id: int) -> Expediente | None:
    """
    Último expediente ``PRORROGA_NOTIFICACION`` activo: mayor ``fecha_expediente``; empate → mayor ``id``.
    """
    rows: List[Expediente] = (
        Expediente.query.filter_by(notificacion_id=int(notificacion_id))
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .all()
    )
    if not rows:
        return None
    return max(
        rows,
        key=lambda r: (
            _as_fecha_expediente_operativa(r.fecha_expediente) or date.min,
            int(r.id),
        ),
    )


def evaluar_expediente_prorroga_permisos(notificacion_id: int, expediente_id: int) -> Dict[str, Any]:
    """
    Permisos de edición/eliminación para un expediente de prórroga concreto.

    Parámetros:
        notificacion_id: PK de la notificación.
        expediente_id: PK del expediente evaluado.

    Retorno:
        dict con ``puede_editar``, ``puede_eliminar``, ``es_ultimo_expediente_activo`` y ``motivos_bloqueo``.

    Errores:
        Ninguno (solo lectura).
    """
    motivos: List[str] = []
    ultimo = _ultimo_expediente_prorroga_activo(notificacion_id)
    es_ultimo = ultimo is not None and int(ultimo.id) == int(expediente_id)
    if not es_ultimo:
        motivos.append(_MSG_BLOQUEO_NO_ULTIMO)
        return {
            "puede_editar": False,
            "puede_eliminar": False,
            "es_ultimo_expediente_activo": False,
            "motivos_bloqueo": motivos,
        }

    usada = notificacion_tiene_reinspeccion_operativamente_usada(notificacion_id)
    if usada:
        motivos.append(_MSG_BLOQUEO_USADA)

    puede = not usada
    return {
        "puede_editar": puede,
        "puede_eliminar": puede,
        "es_ultimo_expediente_activo": True,
        "motivos_bloqueo": motivos,
    }


def evaluar_notificacion_edicion_permisos(act: Actuaciones) -> Dict[str, Any]:
    """
    Evalúa permisos globales de edición del **último** expediente de prórroga de la notificación.

    Parámetros:
        act: actuación con ``notificacion_id`` (rama gestión notificación).

    Retorno:
        dict con flags globales, ``reinspeccion_operativamente_usada`` y motivos de bloqueo.

    Errores:
        Ninguno (solo lectura).
    """
    motivos: List[str] = []

    if act.notificacion_id is None:
        motivos.append("La actuación no tiene notificación asociada.")
        return {
            "puede_editar_expediente_prorroga": False,
            "puede_eliminar_expediente_prorroga": False,
            "notificacion_usada_como_iniciador": False,
            "reinspeccion_operativamente_usada": False,
            "motivos_bloqueo_expediente": motivos,
            "motivos_bloqueo_eliminar_expediente": list(motivos),
        }

    nid = int(act.notificacion_id)
    usada = notificacion_tiene_reinspeccion_operativamente_usada(nid)
    ultimo = _ultimo_expediente_prorroga_activo(nid)

    if ultimo is None:
        motivos.append("No hay expedientes de prórroga activos para editar.")
        puede = False
    elif usada:
        motivos.append(_MSG_BLOQUEO_USADA)
        puede = False
    else:
        puede = True

    return {
        "puede_editar_expediente_prorroga": puede,
        "puede_eliminar_expediente_prorroga": puede,
        "notificacion_usada_como_iniciador": usada,
        "reinspeccion_operativamente_usada": usada,
        "motivos_bloqueo_expediente": motivos,
        "motivos_bloqueo_eliminar_expediente": list(motivos),
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


def _ordenar_expedientes_prorroga_activos(rows: List[Expediente]) -> List[Expediente]:
    """
    Orden cronológico de prórrogas activas: ``fecha_expediente ASC``, ``id ASC``.
    """
    return sorted(
        rows,
        key=lambda r: (
            _as_fecha_expediente_operativa(r.fecha_expediente) or date.min,
            int(r.id),
        ),
    )


def recalcular_vencimiento_notificacion_desde_expedientes(noti: Notificacion) -> None:
    """
    Recalcula ``Notificacion.fecha_vencimiento`` y ``Notificacion.prorroga_dias`` desde expedientes.

    Reglas:
    - Sin prórrogas activas: ``fecha_notificacion + plazo_dias`` (plazo legal inicial).
    - Con prórrogas: cadena acumulada en orden ``fecha_expediente ASC``, ``id ASC``.
      Por cada expediente, si el vencimiento vigente alcanza la fecha del expediente se suman
      días al vencimiento; si ya estaba vencida, se calcula desde ``fecha_expediente``.
    - ``Notificacion.prorroga_dias`` = suma de ``prorroga_dias_otorgados`` activos (DTO).

    Parámetros:
        noti: notificación a mutar (debe tener ``fecha_notificacion``).

    Retorno:
        None (muta ``noti``).

    Errores:
        ValueError: si falta ``fecha_notificacion`` o algún expediente sin ``fecha_expediente``.
    """
    if noti.fecha_notificacion is None:
        raise ValueError("La notificación no tiene fecha_notificacion para recalcular vencimiento")

    rows: List[Expediente] = (
        Expediente.query.filter_by(notificacion_id=noti.id)
        .filter(Expediente.tipo_expediente == "PRORROGA_NOTIFICACION")
        .filter(Expediente.deleted_at.is_(None))
        .all()
    )
    noti.plazo_dias = noti.plazo_dias if noti.plazo_dias is not None else DEFAULT_PLAZO_DIAS
    noti.prorroga_dias = sum(int(r.prorroga_dias_otorgados or 0) for r in rows)

    vencimiento = calcular_fecha_vencimiento(noti.fecha_notificacion, noti.plazo_dias, 0)
    for ex in _ordenar_expedientes_prorroga_activos(rows):
        fecha_base = _as_fecha_expediente_operativa(ex.fecha_expediente)
        if fecha_base is None:
            raise ValueError("El expediente de prórroga no tiene fecha_expediente para recalcular vencimiento")
        plazo = int(ex.prorroga_dias_otorgados or 0)
        modo = "vencimiento_vigente" if vencimiento >= fecha_base else "fecha_expediente"
        vencimiento = aplicar_prorroga_a_vencimiento_acumulado(vencimiento, fecha_base, plazo)
        logger.info(
            "recalc_vencimiento_notificacion notificacion_id=%s expediente_id=%s "
            "fecha_expediente=%s plazo_otorgado=%s modo=%s vencimiento_parcial=%s",
            noti.id,
            ex.id,
            fecha_base.isoformat(),
            plazo,
            modo,
            vencimiento.isoformat(),
        )

    noti.fecha_vencimiento = vencimiento
    db.session.add(noti)


def _recalcular_prorroga_y_vencimiento(noti: Notificacion) -> None:
    """Alias interno al recálculo canónico desde expedientes activos."""
    recalcular_vencimiento_notificacion_desde_expedientes(noti)


def recalcular_prorroga_y_vencimiento_desde_expedientes_activos(noti: Notificacion) -> None:
    """
    Recalcula vencimiento y ``prorroga_dias`` desde filas ``PRORROGA_NOTIFICACION`` activas.

    Parámetros:
        noti: notificación a mutar (debe tener ``fecha_notificacion``).

    Retorno:
        None.

    Errores:
        ValueError: si falta ``fecha_notificacion`` o algún expediente sin ``fecha_expediente``.
    """
    recalcular_vencimiento_notificacion_desde_expedientes(noti)


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

    per = evaluar_expediente_prorroga_permisos(int(noti.id), int(ex.id))
    if not per["puede_editar"]:
        raise ValueError(per["motivos_bloqueo"][0] if per["motivos_bloqueo"] else "Edición no permitida")

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

    recalcular_vencimiento_notificacion_desde_expedientes(noti)
    db.session.flush()
    revoke_reinspeccion_notificacion_iniciadores_obsoletos()
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


def delete_notificacion_prorroga_expediente(actuacion_id: int, expediente_id: int) -> Dict[str, Any]:
    """
    Soft delete de un expediente ``PRORROGA_NOTIFICACION`` y recalculo de plazo/vencimiento.

    Mismas reglas de permiso que ``update_notificacion_prorroga_expediente`` (último activo; bloqueo por uso real).
    Tras marcar ``deleted_at``, se vuelve a sumar ``prorroga_dias`` solo con filas activas y se
    recalcula ``fecha_vencimiento``.

    Parámetros:
        actuacion_id: actuación de contexto.
        expediente_id: PK del expediente de prórroga.

    Retorno:
        dict con ``notificacion`` y ``plazo_notificacion`` serializable (alineado al PATCH).

    Errores:
        LookupError, ValueError, mismos que edición al recalcular vencimiento.
    """
    act, noti, ex = _resolver_notificacion_y_expediente_prorroga(actuacion_id, expediente_id)

    per = evaluar_expediente_prorroga_permisos(int(noti.id), int(ex.id))
    if not per["puede_eliminar"]:
        raise ValueError(per["motivos_bloqueo"][0] if per["motivos_bloqueo"] else "Eliminación no permitida")

    ex.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex)

    recalcular_vencimiento_notificacion_desde_expedientes(noti)
    db.session.flush()
    revoke_reinspeccion_notificacion_iniciadores_obsoletos()
    db.session.commit()

    return {
        "notificacion": noti,
        "plazo_notificacion": {
            "plazo_legal_dias": noti.plazo_dias,
            "prorroga_total_dias": noti.prorroga_dias,
            "fecha_notificacion": noti.fecha_notificacion.isoformat() if noti.fecha_notificacion else None,
            "fecha_vencimiento": noti.fecha_vencimiento.isoformat() if noti.fecha_vencimiento else None,
        },
    }
