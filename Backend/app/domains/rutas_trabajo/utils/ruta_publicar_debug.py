"""
PR11.1d — Trazabilidad diagnóstica al publicar ruta (temporal / QA).

No altera reglas de negocio: solo logs estructurados, payloads debug en 409
y utilidades para scripts de relevamiento.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import Actuaciones, IniciadorRuta, OrdenTrabajo, RutaItem, RutaTrabajo

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[PR11.1d publicar debug]"


def publicar_debug_habilitado() -> bool:
    """True si los 409 de publicar deben incluir bloque ``debug`` en JSON."""
    return os.environ.get("RUTA_PUBLICAR_DEBUG", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


class RutaPublicarDebugError(RuntimeError):
    """
    Error de negocio al publicar con contexto diagnóstico para QA.

    Parámetros:
        message: mensaje legible para el usuario.
        debug: mapa con ids, estados y validador que disparó el bloqueo.
    """

    def __init__(self, message: str, *, debug: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.debug: dict[str, Any] = dict(debug or {})


def log_publicar_debug(
    *,
    conflicto_detectado_por: str,
    mensaje_conflicto: str | None = None,
    **campos: Any,
) -> dict[str, Any]:
    """
    Emite log estructurado PR11.1d y devuelve el mismo mapa para adjuntar a 409.

    Parámetros:
        conflicto_detectado_por: módulo/función que detectó el bloqueo.
        mensaje_conflicto: texto del error si aplica.
        **campos: pares clave/valor del contexto operativo.

    Retorno:
        Diccionario con todos los campos del log.
    """
    payload: dict[str, Any] = {
        "conflicto_detectado_por": conflicto_detectado_por,
        "mensaje_conflicto": mensaje_conflicto,
    }
    payload.update({k: v for k, v in campos.items() if v is not None})
    partes = [f"{_LOG_PREFIX} {conflicto_detectado_por}"]
    for key in sorted(payload):
        if key in ("conflicto_detectado_por", "mensaje_conflicto"):
            continue
        partes.append(f"{key}={payload[key]!r}")
    if mensaje_conflicto:
        partes.append(f"mensaje={mensaje_conflicto!r}")
    logger.warning(" | ".join(partes))
    return payload


def _iso_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def log_before_commit_publicar_ruta(
    *,
    ruta_id: int,
    items_debug: list[dict[str, Any]],
) -> None:
    """
    PR11.1f — Log diagnóstico inmediatamente antes del commit de publicar.

    Parámetros:
        ruta_id: ruta en publicación.
        items_debug: contexto por ítem armado durante el bucle de persistencia.

    Retorno:
        None (solo emite logs).
    """
    prefix = "[PR11.1f before commit]"
    logger.warning("%s ruta_id=%r inicio items=%d", prefix, ruta_id, len(items_debug))

    for row in items_debug:
        partes = [f"{prefix} item"]
        for key in (
            "item_id",
            "iniciador_id",
            "orden_trabajo_id",
            "numero_orden_trabajo",
            "actuacion_resuelta_id",
            "actuacion_previa_id",
            "actuacion_a_usar_id",
            "modo_persistencia",
            "item_actuacion_id_antes",
            "item_actuacion_id_despues",
            "act_orden_trabajo_id_antes",
            "act_orden_trabajo_id_despues",
        ):
            if key in row and row[key] is not None:
                partes.append(f"{key}={row[key]!r}")
        logger.warning(" | ".join(partes))

    new_objs = list(db.session.new)
    dirty_objs = list(db.session.dirty)
    deleted_objs = list(db.session.deleted)
    logger.warning(
        "%s session ruta_id=%r new=%d dirty=%d deleted=%d",
        prefix,
        ruta_id,
        len(new_objs),
        len(dirty_objs),
        len(deleted_objs),
    )

    for act in list(new_objs) + list(dirty_objs):
        if not isinstance(act, Actuaciones):
            continue
        item_rel = (
            RutaItem.query.filter(RutaItem.actuacion_id == act.id)
            .order_by(RutaItem.id.desc())
            .first()
        )
        ini_rel = (
            item_rel.iniciador_ruta_id
            if item_rel is not None
            else None
        )
        estado = "new" if act in new_objs else "dirty"
        logger.warning(
            "%s actuacion_%s id=%r tipo=%r orden_trabajo_id=%r iniciador_item=%r "
            "notificacion_id=%r comprobacion_id=%r contraproducencia=%r "
            "estado_ejecucion_n/a",
            prefix,
            estado,
            act.id,
            act.tipo,
            act.orden_trabajo_id,
            ini_rel,
            act.notificacion_id,
            act.comprobacion_id,
            act.contraproducencia,
        )


def snapshot_item_publicar_context(
    *,
    ruta: RutaTrabajo | None,
    item: RutaItem,
    iniciador: IniciadorRuta | None = None,
    actuacion_previa: Actuaciones | None = None,
    ruta_item_previo: RutaItem | None = None,
    ruta_previa: RutaTrabajo | None = None,
) -> dict[str, Any]:
    """
    Arma contexto diagnóstico de un ítem en publicación.

    Parámetros:
        ruta: ruta en publicación.
        item: ítem activo.
        iniciador: iniciador del ítem (opcional si no está cargado).
        actuacion_previa: actuación reintento detectada.
        ruta_item_previo: ítem previo del mismo iniciador (si se conoce).
        ruta_previa: ruta del ítem previo.

    Retorno:
        Mapa serializable para logs y respuesta 409.
    """
    ini = iniciador or item.iniciador_ruta
    ot = item.orden_trabajo
    act_prev = actuacion_previa
    if act_prev is None and ini is not None:
        from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
            buscar_actuacion_reintento_reutilizable,
        )

        act_prev = buscar_actuacion_reintento_reutilizable(int(ini.id))

    ctx: dict[str, Any] = {
        "ruta_id": ruta.id if ruta else item.ruta_trabajo_id,
        "ruta_fecha": _iso_date(ruta.fecha if ruta else None),
        "item_id": item.id,
        "grupo_id": item.ruta_grupo_id,
        "iniciador_id": ini.id if ini else item.iniciador_ruta_id,
        "tipo_iniciador": ini.tipo_iniciador if ini else None,
        "estado_iniciador": ini.estado_iniciador if ini else None,
        "orden_trabajo_id": item.orden_trabajo_id,
        "numero_orden_trabajo": ot.numero_acta if ot else None,
        "actuacion_id_actual": item.actuacion_id,
        "actuacion_previa_id": act_prev.id if act_prev else None,
        "actuacion_previa_contraproducencia": act_prev.contraproducencia if act_prev else None,
        "actuacion_previa_orden_trabajo_id": act_prev.orden_trabajo_id if act_prev else None,
    }
    if ruta_item_previo is not None:
        ctx.update(
            {
                "ruta_item_previo_id": ruta_item_previo.id,
                "ruta_item_previo_estado": ruta_item_previo.estado_ruta_item,
                "ruta_item_previo_estado_ejecucion": ruta_item_previo.estado_ejecucion,
                "ruta_item_previo_soft_deleted": ruta_item_previo.deleted_at is not None,
                "ruta_previa_id": ruta_item_previo.ruta_trabajo_id,
            }
        )
    if ruta_previa is not None:
        ctx["ruta_previa_estado"] = ruta_previa.estado_ruta
    elif ruta_item_previo is not None:
        ruta_db = db.session.get(RutaTrabajo, ruta_item_previo.ruta_trabajo_id)
        ctx["ruta_previa_estado"] = ruta_db.estado_ruta if ruta_db else None
    return ctx


def parse_integrity_error(exc: IntegrityError) -> dict[str, Any]:
    """
    Extrae constraint, tabla y detalle de un IntegrityError de SQLAlchemy/MySQL.

    Parámetros:
        exc: excepción capturada en commit/flush.

    Retorno:
        Mapa con ``constraint_name``, ``table``, ``columns``, ``message``, ``orig``.
    """
    orig = getattr(exc, "orig", None)
    message = str(orig or exc)
    info: dict[str, Any] = {
        "tipo": "IntegrityError",
        "message": message,
        "orig": repr(orig),
    }
    if orig is not None:
        info["errno"] = getattr(orig, "args", [None])[0]
    m_dup = re.search(
        r"Duplicate entry '([^']*)' for key '([^']+)'",
        message,
        re.IGNORECASE,
    )
    if m_dup:
        info["duplicate_value"] = m_dup.group(1)
        info["constraint_name"] = m_dup.group(2)
    m_fk = re.search(r"FOREIGN KEY \(`([^`]+)`\)", message)
    if m_fk:
        info["column"] = m_fk.group(1)
    if "actuaciones" in message.lower():
        info["tabla_probable"] = "actuaciones"
    elif "orden_trabajo" in message.lower():
        info["tabla_probable"] = "orden_trabajo"
    elif "ruta_item" in message.lower():
        info["tabla_probable"] = "ruta_item"
    if "orden_trabajo_id" in message:
        info["columns_probables"] = ["orden_trabajo_id"]
    if "uq_act_anio_tipo_notificacion" in message:
        info["constraint_name"] = "uq_act_anio_tipo_notificacion"
        info["columns_probables"] = ["anio", "tipo", "notificacion_id"]
    if "uq_act_anio_tipo_comprobacion" in message:
        info["constraint_name"] = "uq_act_anio_tipo_comprobacion"
        info["columns_probables"] = ["anio", "tipo", "comprobacion_id"]
    return info


def raise_publicar_debug(
    message: str,
    *,
    validator: str,
    debug: dict[str, Any] | None = None,
    cause: BaseException | None = None,
) -> None:
    """
    Loguea y lanza ``RutaPublicarDebugError`` con contexto unificado.

    Errores:
        RutaPublicarDebugError: siempre.
    """
    payload = log_publicar_debug(
        conflicto_detectado_por=validator,
        mensaje_conflicto=message,
        **(debug or {}),
    )
    payload["validator"] = validator
    err = RutaPublicarDebugError(message, debug=payload)
    if cause is not None:
        raise err from cause
    raise err


def conflicto_ot_a_debug(
    conflicto: Any,
    *,
    ruta: RutaTrabajo | None,
    item: RutaItem,
    iniciador: IniciadorRuta,
    act_bloqueante: Actuaciones | None = None,
) -> dict[str, Any]:
    """Convierte ``ConflictoOrdenTrabajoPublicar`` + contexto a mapa debug."""
    act = act_bloqueante or db.session.get(Actuaciones, conflicto.actuacion_id)
    from app.domains.rutas_trabajo.services.ruta_publicar_ot_conflicto_service import (
        actuacion_reserva_orden_trabajo,
    )

    ctx = snapshot_item_publicar_context(ruta=ruta, item=item, iniciador=iniciador)
    item_previo = None
    if conflicto.ruta_item_id is not None:
        item_previo = db.session.get(RutaItem, conflicto.ruta_item_id)
    if item_previo is not None:
        ctx.update(
            {
                "ruta_item_previo_id": item_previo.id,
                "ruta_item_previo_estado": item_previo.estado_ruta_item,
                "ruta_item_previo_estado_ejecucion": item_previo.estado_ejecucion,
                "ruta_item_previo_soft_deleted": item_previo.deleted_at is not None,
                "ruta_previa_id": item_previo.ruta_trabajo_id,
            }
        )
    ctx.update(
        {
            "validator": "buscar_conflicto_orden_trabajo_al_publicar",
            "actuacion_bloqueante_id": conflicto.actuacion_id,
            "item_bloqueante_id": conflicto.ruta_item_id,
            "estado_item_bloqueante": conflicto.estado_ruta_item,
            "estado_ejecucion_bloqueante": conflicto.estado_ejecucion,
            "ruta_bloqueante_id": conflicto.ruta_trabajo_id,
            "estado_ruta_bloqueante": conflicto.estado_ruta,
            "contraproducencia_bloqueante": act.contraproducencia if act else None,
            "notificacion_id_bloqueante": act.notificacion_id if act else None,
            "comprobacion_id_bloqueante": act.comprobacion_id if act else None,
            "actuacion_bloqueante_reserva_ot": (
                actuacion_reserva_orden_trabajo(act) if act else None
            ),
        }
    )
    return ctx


def json_409_publicar(exc: Exception) -> tuple[dict[str, Any], int]:
    """
    Arma cuerpo JSON para respuesta 409 de publicar con debug opcional.

    Parámetros:
        exc: excepción capturada en la ruta HTTP.

    Retorno:
        Tupla (body, status_code).
    """
    body: dict[str, Any] = {"detail": str(exc)}
    if isinstance(exc, RutaPublicarDebugError) and publicar_debug_habilitado():
        body["debug"] = exc.debug
    elif isinstance(exc, IntegrityError) and publicar_debug_habilitado():
        body["debug"] = {
            "validator": "IntegrityError_commit_publicar",
            **parse_integrity_error(exc),
        }
    return body, 409

