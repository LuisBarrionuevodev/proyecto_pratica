"""
Documental operativo de comprobación: lectura consolidada y edición/eliminación controlada de expediente de envío
y bloque oficio + expediente de respuesta.

Regla de bloqueo:
- Si existe ``IniciadorRuta`` no borrado con ``comprobacion_id`` de esta comprobación, la comprobación
  se considera **ya usada como iniciador** y no se permite editar expediente de envío ni oficio/respuesta.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.database import db
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.domains.actuaciones.presenters.comprobacion_actas_presenters import referencia_actuacion_from_grid_row
from app.models import Actuaciones, Expediente, IniciadorRuta, JuzgadoCatalogo, Oficio
from app.utils.actas import acta_6


_MSG_BLOQUEO = (
    "No se puede editar porque la comprobación ya fue usada como iniciador "
    "(existe un registro activo en iniciador_ruta vinculado a esta comprobación)."
)

_MSG_NO_ELIMINAR_ENVIO_CON_OFICIO = (
    "No se puede eliminar el expediente de envío: ya existe un oficio activo para esta comprobación. "
    "Si corresponde, eliminá primero el bloque oficio y expediente de respuesta."
)


def comprobacion_usada_como_iniciador(comprobacion_id: int) -> bool:
    """
    Indica si la comprobación tiene al menos un iniciador de rutas activo vinculado por ``comprobacion_id``.

    Parámetros:
        comprobacion_id: PK de ``comprobacion``.

    Retorno:
        True si hay ``IniciadorRuta`` con ``deleted_at`` nulo y ese ``comprobacion_id``.
    """
    return (
        db.session.query(IniciadorRuta.id)
        .filter(
            IniciadorRuta.comprobacion_id == int(comprobacion_id),
            IniciadorRuta.deleted_at.is_(None),
        )
        .limit(1)
        .first()
        is not None
    )


def evaluar_comprobacion_edicion_documental(act: Actuaciones) -> Dict[str, Any]:
    """
    Evalúa permisos de edición documental (expediente envío y bloque oficio) para la actuación.

    Parámetros:
        act: actuación con ``comprobacion_id``.

    Retorno:
        dict con flags y mensajes de bloqueo.
    """
    motivos_exp: List[str] = []
    motivos_ofi: List[str] = []
    if act.comprobacion_id is None:
        motivos_exp.append("La actuación no tiene comprobación asociada.")
        motivos_ofi.append("La actuación no tiene comprobación asociada.")
        return {
            "comprobacion_usada_como_iniciador": False,
            "puede_editar_expediente_envio": False,
            "puede_editar_bloque_oficio": False,
            "puede_eliminar_expediente_envio": False,
            "puede_eliminar_bloque_oficio": False,
            "motivos_bloqueo_expediente_envio": motivos_exp,
            "motivos_bloqueo_oficio": motivos_ofi,
            "motivos_bloqueo_eliminar_expediente_envio": list(motivos_exp),
            "motivos_bloqueo_eliminar_bloque_oficio": list(motivos_ofi),
        }

    cid = int(act.comprobacion_id)
    usada = comprobacion_usada_como_iniciador(cid)
    if usada:
        motivos_exp.append(_MSG_BLOQUEO)
        motivos_ofi.append(_MSG_BLOQUEO)

    ex_env = _get_expediente_envio(cid)
    ofi = _get_oficio_activo(cid)
    ex_resp = _get_expediente_respuesta(ofi.id) if ofi else None

    puede_exp = (not usada) and (ex_env is not None)
    puede_ofi = (not usada) and (ofi is not None) and (ex_resp is not None)

    motivos_del_env: List[str] = []
    if ex_env is None:
        motivos_del_env.append("No hay expediente de envío activo para eliminar.")
    if usada:
        motivos_del_env.append(_MSG_BLOQUEO)
    elif ofi is not None:
        motivos_del_env.append(_MSG_NO_ELIMINAR_ENVIO_CON_OFICIO)
    puede_del_env = (not usada) and (ex_env is not None) and (ofi is None)

    motivos_del_ofi: List[str] = []
    if usada:
        motivos_del_ofi.append(_MSG_BLOQUEO)
    if ofi is None or ex_resp is None:
        motivos_del_ofi.append("No hay oficio y expediente de respuesta activos para eliminar en bloque.")
    puede_del_ofi = puede_ofi and (ofi is not None) and (ex_resp is not None)

    return {
        "comprobacion_usada_como_iniciador": usada,
        "puede_editar_expediente_envio": puede_exp,
        "puede_editar_bloque_oficio": puede_ofi,
        "puede_eliminar_expediente_envio": puede_del_env,
        "puede_eliminar_bloque_oficio": puede_del_ofi,
        "motivos_bloqueo_expediente_envio": motivos_exp,
        "motivos_bloqueo_oficio": motivos_ofi,
        "motivos_bloqueo_eliminar_expediente_envio": motivos_del_env,
        "motivos_bloqueo_eliminar_bloque_oficio": motivos_del_ofi,
    }


def _get_expediente_envio(comprobacion_id: int) -> Optional[Expediente]:
    return (
        Expediente.query.filter_by(comprobacion_id=comprobacion_id, oficio_id=None)
        .filter(Expediente.tipo_expediente == "ENVIO_ACTA")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def _get_oficio_activo(comprobacion_id: int) -> Optional[Oficio]:
    return (
        Oficio.query.filter_by(comprobacion_id=comprobacion_id)
        .filter(Oficio.deleted_at.is_(None))
        .order_by(Oficio.id.desc())
        .first()
    )


def _get_expediente_respuesta(oficio_id: int) -> Optional[Expediente]:
    return (
        Expediente.query.filter_by(oficio_id=oficio_id, tipo_expediente="RESPUESTA_OFICIO")
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def _expediente_to_item(ex: Expediente) -> Dict[str, Any]:
    return {
        "id": ex.id,
        "numero_expediente": ex.numero_expediente,
        "anio": ex.anio,
        "fecha_expediente": ex.fecha_expediente.isoformat() if ex.fecha_expediente else None,
        "tipo_expediente": ex.tipo_expediente,
        "oficio_id": ex.oficio_id,
    }


def _oficio_to_item(of: Oficio) -> Dict[str, Any]:
    j = db.session.get(JuzgadoCatalogo, int(of.juzgado_id)) if of.juzgado_id else None
    return {
        "id": of.id,
        "numero_oficio": of.numero_oficio,
        "anio": of.anio,
        "fecha_oficio": of.fecha_oficio.isoformat() if of.fecha_oficio else None,
        "causa": of.causa,
        "juzgado_id": of.juzgado_id,
        "juzgado_nombre": j.nombre if j else None,
    }


def get_comprobacion_documental_for_actuacion(actuacion_id: int) -> Dict[str, Any]:
    """
    Devuelve expediente de envío, oficio y expediente de respuesta (si existen) más permisos de edición.

    Parámetros:
        actuacion_id: PK de la actuación.

    Retorno:
        dict serializable con ``actuacion_id``, ``comprobacion_id``, ``referencia_actuacion``,
        ``acta_comprobacion`` (número/motivo), ``expediente_envio``, ``oficio``, ``expediente_respuesta``,
        ``edicion``.

    Errores:
        LookupError: actuación inexistente.
        ValueError: actuación sin comprobación.
    """
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.comprobacion_id is None:
        raise ValueError("La actuación no tiene comprobación asociada")

    cid = int(act.comprobacion_id)
    ex_env = _get_expediente_envio(cid)
    ofi = _get_oficio_activo(cid)
    ex_resp = _get_expediente_respuesta(ofi.id) if ofi else None

    grid = actuacion_to_grid_row(act)
    ref = referencia_actuacion_from_grid_row(grid)
    acta_comp = {
        "numero": grid.get("acta_comprobacion_num"),
        "motivo": grid.get("comprobacion_motivo"),
    }

    return {
        "actuacion_id": act.id,
        "comprobacion_id": cid,
        "referencia_actuacion": ref,
        "acta_comprobacion": acta_comp,
        "expediente_envio": _expediente_to_item(ex_env) if ex_env else None,
        "oficio": _oficio_to_item(ofi) if ofi else None,
        "expediente_respuesta": _expediente_to_item(ex_resp) if ex_resp else None,
        "edicion": evaluar_comprobacion_edicion_documental(act),
    }


def _resolver_actuacion_comprobacion_expediente_envio(
    actuacion_id: int, expediente_id: int
) -> Tuple[Actuaciones, Expediente]:
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.comprobacion_id is None:
        raise ValueError("La actuación no tiene comprobación asociada")

    ex = db.session.get(Expediente, expediente_id)
    if ex is None or ex.deleted_at is not None:
        raise LookupError("Expediente no encontrado")
    if ex.comprobacion_id != int(act.comprobacion_id):
        raise ValueError("El expediente no pertenece a la comprobación de esta actuación")
    if ex.oficio_id is not None:
        raise ValueError("Solo se edita el expediente de envío (sin oficio vinculado)")
    if ex.tipo_expediente != "ENVIO_ACTA":
        raise ValueError("Solo se pueden editar expedientes de envío de acta (ENVIO_ACTA)")

    return act, ex


def update_comprobacion_expediente_envio(
    actuacion_id: int,
    expediente_id: int,
    *,
    numero_expediente: str,
    fecha_expediente: date,
) -> Dict[str, Any]:
    """
    Actualiza número y fecha del expediente de envío de comprobación.

    Parámetros:
        actuacion_id: actuación cuyo contexto de comprobación se valida.
        expediente_id: PK del expediente ``ENVIO_ACTA`` con ``oficio_id`` nulo.
        numero_expediente: número normalizado (``acta_6``).
        fecha_expediente: fecha del expediente (define ``anio`` contable).

    Retorno:
        dict con ``expediente`` (ORM) e ``item`` serializable.

    Errores:
        LookupError / ValueError / RuntimeError (409 duplicado).
    """
    act, ex = _resolver_actuacion_comprobacion_expediente_envio(actuacion_id, expediente_id)

    per = evaluar_comprobacion_edicion_documental(act)
    if not per["puede_editar_expediente_envio"]:
        raise ValueError(
            per["motivos_bloqueo_expediente_envio"][0]
            if per["motivos_bloqueo_expediente_envio"]
            else "Edición del expediente de envío no permitida"
        )

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
    db.session.add(ex)
    db.session.commit()

    return {"expediente": ex, "item": _expediente_to_item(ex)}


def delete_comprobacion_expediente_envio(actuacion_id: int, expediente_id: int) -> None:
    """
    Marca como borrado (soft delete) el expediente de envío ``ENVIO_ACTA`` de la comprobación.

    Reglas:
    - Misma resolución de contexto que ``update_comprobacion_expediente_envio``.
    - No permitido si la comprobación está usada como iniciador de ruta.
    - No permitido si ya existe un oficio activo para la comprobación (el circuito documental avanzó).

    Parámetros:
        actuacion_id: actuación de contexto.
        expediente_id: PK del expediente de envío.

    Retorno:
        None.

    Errores:
        LookupError / ValueError según validación de pertenencia o permisos.
    """
    act, ex = _resolver_actuacion_comprobacion_expediente_envio(actuacion_id, expediente_id)

    per = evaluar_comprobacion_edicion_documental(act)
    if not per["puede_eliminar_expediente_envio"]:
        raise ValueError(
            per["motivos_bloqueo_eliminar_expediente_envio"][0]
            if per["motivos_bloqueo_eliminar_expediente_envio"]
            else "Eliminación del expediente de envío no permitida"
        )

    ex.deleted_at = datetime.now(timezone.utc)
    db.session.add(ex)
    db.session.commit()


def delete_comprobacion_oficio_bloque(actuacion_id: int, oficio_id: int) -> None:
    """
    Soft delete del oficio y del expediente de respuesta vinculado (misma transacción).

    Reglas:
    - Misma resolución que ``update_comprobacion_oficio_bloque`` (debe existir expediente de respuesta).
    - No permitido si la comprobación está usada como iniciador de ruta (misma política que edición).

    Parámetros:
        actuacion_id: actuación de contexto.
        oficio_id: PK del oficio.

    Retorno:
        None.

    Errores:
        LookupError / ValueError.
    """
    act, ofi, ex_resp = _resolver_actuacion_oficio_bloque(actuacion_id, oficio_id)

    per = evaluar_comprobacion_edicion_documental(act)
    if not per["puede_eliminar_bloque_oficio"]:
        raise ValueError(
            per["motivos_bloqueo_eliminar_bloque_oficio"][0]
            if per["motivos_bloqueo_eliminar_bloque_oficio"]
            else "Eliminación del bloque oficio no permitida"
        )

    now = datetime.now(timezone.utc)
    ex_resp.deleted_at = now
    ofi.deleted_at = now
    db.session.add(ex_resp)
    db.session.add(ofi)
    db.session.commit()


def _resolver_actuacion_oficio_bloque(actuacion_id: int, oficio_id: int) -> Tuple[Actuaciones, Oficio, Expediente]:
    act = db.session.get(Actuaciones, actuacion_id)
    if act is None:
        raise LookupError("Actuación no encontrada")
    if act.comprobacion_id is None:
        raise ValueError("La actuación no tiene comprobación asociada")

    ofi = db.session.get(Oficio, oficio_id)
    if ofi is None or ofi.deleted_at is not None:
        raise LookupError("Oficio no encontrado")
    if ofi.comprobacion_id != int(act.comprobacion_id):
        raise ValueError("El oficio no pertenece a la comprobación de esta actuación")

    ex_resp = _get_expediente_respuesta(ofi.id)
    if ex_resp is None:
        raise ValueError("No existe expediente de respuesta de oficio para este oficio")

    return act, ofi, ex_resp


def update_comprobacion_oficio_bloque(
    actuacion_id: int,
    oficio_id: int,
    *,
    numero_oficio: str,
    fecha_oficio: date,
    juzgado_id: int,
    causa: Optional[str],
    numero_expediente_respuesta: str,
    fecha_expediente_respuesta: date,
) -> Dict[str, Any]:
    """
    Actualiza oficio (número, año derivado de fecha, fecha, juzgado, causa) y expediente de respuesta vinculado.

    Parámetros:
        actuacion_id: actuación de contexto.
        oficio_id: PK del oficio de la comprobación.
        numero_oficio: número de oficio (texto).
        fecha_oficio: fecha del oficio; el año contable del oficio se alinea con ``fecha_oficio.year``.
        juzgado_id: FK a catálogo de juzgados.
        causa: texto opcional (unicidad por año si no nula).
        numero_expediente_respuesta: número del expediente de respuesta (``acta_6``).
        fecha_expediente_respuesta: fecha del expediente de respuesta; debe coincidir con ``fecha_oficio``
            (si difiere, el servicio la fuerza a ``fecha_oficio``).

    Retorno:
        dict con ``oficio``, ``expediente_respuesta`` e items serializables.

    Errores:
        LookupError, ValueError, RuntimeError (unicidad).
    """
    act, ofi, ex_resp = _resolver_actuacion_oficio_bloque(actuacion_id, oficio_id)

    if fecha_expediente_respuesta != fecha_oficio:
        fecha_expediente_respuesta = fecha_oficio

    per = evaluar_comprobacion_edicion_documental(act)
    if not per["puede_editar_bloque_oficio"]:
        raise ValueError(
            per["motivos_bloqueo_oficio"][0] if per["motivos_bloqueo_oficio"] else "Edición del oficio no permitida"
        )

    j = db.session.get(JuzgadoCatalogo, int(juzgado_id))
    if j is None:
        raise LookupError("Juzgado no encontrado")

    num_ofi = str(numero_oficio).strip()
    if not num_ofi:
        raise ValueError("numero_oficio es obligatorio")

    anio_ofi = int(fecha_oficio.year)

    dup_ofi = (
        Oficio.query.filter(Oficio.numero_oficio == num_ofi, Oficio.anio == anio_ofi)
        .filter(Oficio.id != ofi.id)
        .filter(Oficio.deleted_at.is_(None))
        .first()
    )
    if dup_ofi:
        raise RuntimeError("Ya existe otro oficio con ese número y año")

    causa_n = str(causa).strip() if causa is not None else None
    if causa_n == "":
        causa_n = None
    if causa_n is not None:
        dup_causa = (
            Oficio.query.filter(Oficio.causa == causa_n, Oficio.anio == anio_ofi)
            .filter(Oficio.id != ofi.id)
            .filter(Oficio.deleted_at.is_(None))
            .first()
        )
        if dup_causa:
            raise ValueError(f'La causa "{causa_n}" ya existe para el año {anio_ofi}.')

    num_ex = acta_6(numero_expediente_respuesta)
    if not num_ex:
        raise ValueError("numero_expediente_respuesta inválido")
    anio_ex = str(fecha_expediente_respuesta.year)

    dup_ex = (
        Expediente.query.filter(Expediente.numero_expediente == num_ex, Expediente.anio == anio_ex)
        .filter(Expediente.id != ex_resp.id)
        .filter(Expediente.deleted_at.is_(None))
        .first()
    )
    if dup_ex:
        raise RuntimeError("Ya existe otro expediente con ese número y año")

    ofi.numero_oficio = num_ofi
    ofi.anio = anio_ofi
    ofi.fecha_oficio = fecha_oficio
    ofi.juzgado_id = int(juzgado_id)
    ofi.causa = causa_n
    db.session.add(ofi)

    ex_resp.numero_expediente = num_ex
    ex_resp.fecha_expediente = fecha_expediente_respuesta
    ex_resp.anio = anio_ex
    db.session.add(ex_resp)

    db.session.commit()

    return {
        "oficio": ofi,
        "expediente_respuesta": ex_resp,
        "oficio_item": _oficio_to_item(ofi),
        "expediente_respuesta_item": _expediente_to_item(ex_resp),
    }
