"""
Materialización diferida de iniciadores desde oficios documentales.
"""

from __future__ import annotations

from typing import List, Optional

from app.database import db
from app.domains.actuaciones.services.comprobacion_oficio_recorrido_service import (
    iniciador_reinspeccion_por_oficio,
)
from app.domains.actuaciones.services.oficio_iniciador_service import (
    get_or_create_iniciador_from_oficio,
)
from app.domains.actuaciones.utils.iniciador_materializacion_estado import (
    MATERIALIZADO,
    PENDIENTE_DOMICILIO,
    PENDIENTE_MATERIALIZACION,
)
from app.domains.rutas_trabajo.services.auth_service import validate_actor_user_id
from app.models import Actuaciones, Expediente, IniciadorRuta, Oficio
from sqlalchemy import or_


def _expediente_respuesta_activo(oficio_id: int) -> Expediente | None:
    return (
        Expediente.query.filter_by(oficio_id=int(oficio_id))
        .filter(
            or_(
                Expediente.tipo_expediente == "RESPUESTA_OFICIO",
                Expediente.tipo_expediente.is_(None),
            )
        )
        .filter(Expediente.deleted_at.is_(None))
        .order_by(Expediente.id.asc())
        .first()
    )


def materializar_iniciador_oficio_si_posible(
    oficio_id: int,
    actuacion: Actuaciones,
    *,
    actor_user_id: int,
    expediente_respuesta: Expediente | None = None,
) -> Optional[IniciadorRuta]:
    """
    Crea o reutiliza iniciador para un oficio pendiente de materialización.

    Parámetros:
        oficio_id: PK del oficio.
        actuacion: actuación ancla (debe tener comprobación coherente).
        actor_user_id: usuario auditor.
        expediente_respuesta: opcional; si falta se resuelve desde BD.

    Retorno:
        IniciadorRuta si se materializó; None si domicilio ausente o ya materializado.

    Errores:
        ValueError: datos inválidos.
        LookupError: oficio inexistente.
    """
    uid = validate_actor_user_id(actor_user_id)
    oficio = db.session.get(Oficio, int(oficio_id))
    if oficio is None or oficio.deleted_at is not None:
        raise LookupError("Oficio no encontrado")

    if oficio.iniciador_materializacion_estado == MATERIALIZADO:
        return iniciador_reinspeccion_por_oficio(oficio.id)

    if act.domicilio_id is None:
        oficio.iniciador_materializacion_estado = PENDIENTE_DOMICILIO
        db.session.add(oficio)
        return None

    ex_resp = expediente_respuesta or _expediente_respuesta_activo(oficio.id)
    if ex_resp is None:
        raise ValueError("No existe expediente de respuesta de oficio")

    iniciador = get_or_create_iniciador_from_oficio(
        actuacion=actuacion,
        oficio=oficio,
        expediente_respuesta=ex_resp,
        actor_user_id=uid,
    )
    if iniciador.id is None:
        db.session.add(iniciador)
    oficio.iniciador_materializacion_estado = MATERIALIZADO
    db.session.add(oficio)
    return iniciador


def materializar_iniciador_tras_oficio_documental(
    actuacion: Actuaciones,
    oficio: Oficio,
    expediente_respuesta: Expediente,
    *,
    actor_user_id: int,
) -> Optional[IniciadorRuta]:
    """
    Orquesta materialización inmediata post-alta de oficio según domicilio.

    Parámetros:
        actuacion: actuación destino.
        oficio: oficio recién persistido o existente.
        expediente_respuesta: expediente RESPUESTA_OFICIO activo.
        actor_user_id: usuario auditor.

    Retorno:
        Iniciador si domicilio presente; None si queda PENDIENTE_DOMICILIO.

    Errores:
        ValueError: fallo inesperado al crear iniciador (rollback del llamador).
    """
    if actuacion.domicilio_id is None:
        oficio.iniciador_materializacion_estado = PENDIENTE_DOMICILIO
        db.session.add(oficio)
        return None

    iniciador = get_or_create_iniciador_from_oficio(
        actuacion=actuacion,
        oficio=oficio,
        expediente_respuesta=expediente_respuesta,
        actor_user_id=actor_user_id,
    )
    if iniciador.id is None:
        db.session.add(iniciador)
    oficio.iniciador_materializacion_estado = MATERIALIZADO
    db.session.add(oficio)
    return iniciador


def materializar_iniciadores_oficio_pendientes_para_actuacion(
    act: Actuaciones,
    *,
    actor_user_id: int,
) -> List[IniciadorRuta]:
    """
    Intenta materializar oficios PENDIENTE_* de la comprobación cuando hay domicilio.

    Parámetros:
        act: actuación con comprobación y opcional domicilio recién asignado.
        actor_user_id: usuario auditor.

    Retorno:
        Lista de iniciadores materializados en esta invocación.
    """
    if act.comprobacion_id is None or act.domicilio_id is None:
        return []

    oficios = (
        Oficio.query.filter_by(comprobacion_id=int(act.comprobacion_id))
        .filter(Oficio.deleted_at.is_(None))
        .filter(
            Oficio.iniciador_materializacion_estado.in_(
                (PENDIENTE_DOMICILIO, PENDIENTE_MATERIALIZACION)
            )
        )
        .all()
    )
    out: List[IniciadorRuta] = []
    for ofi in oficios:
        ini = materializar_iniciador_oficio_si_posible(
            ofi.id,
            act,
            actor_user_id=actor_user_id,
        )
        if ini is not None:
            out.append(ini)
    return out
