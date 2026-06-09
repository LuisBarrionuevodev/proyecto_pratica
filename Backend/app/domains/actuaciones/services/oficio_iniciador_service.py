from __future__ import annotations

from datetime import date

from flask_jwt_extended import get_jwt_identity

from app.models import Actuaciones, Expediente, IniciadorRuta, Oficio, User
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    assign_iniciador_domicilio_desde_origen,
    resolve_domicilio_operativo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)


def _get_current_user_id() -> int:
    """
    Obtiene el usuario autenticado actual desde JWT.

    Raises:
        ValueError: si no hay usuario válido/autorizado.
    """
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    user_id = identity.get("user_id") if isinstance(identity, dict) else identity
    if user_id is not None:
        try:
            parsed_id = int(user_id)
        except (TypeError, ValueError):
            parsed_id = None
        if parsed_id is not None:
            user = User.query.get(parsed_id)
            if user and getattr(user, "is_active", True):
                return parsed_id

    # Fallback operativo para endpoints legacy no protegidos con JWT.
    fallback_user = (
        User.query.filter(User.is_active.is_(True))
        .order_by(User.id.asc())
        .first()
    )
    if fallback_user:
        return int(fallback_user.id)
    raise ValueError("No hay usuario activo para registrar created_by_user_id")


def get_or_create_iniciador_from_oficio(
    *,
    actuacion: Actuaciones,
    oficio: Oficio,
    expediente_respuesta: Expediente,
) -> IniciadorRuta:
    """
    Crea (o recupera) un iniciador derivado desde oficio en estado neutral pendiente.

    Parámetros:
        expediente_respuesta: expediente de **respuesta de oficio** (no el de envío de comprobación).

    Reglas:
    - `tipo_iniciador` inicial: REINSPECCION_OFICIO.
    - Idempotente: no duplica iniciadores activos del mismo oficio.
    """
    existente = (
        IniciadorRuta.query.filter(
            IniciadorRuta.oficio_id == oficio.id,
            IniciadorRuta.tipo_iniciador == "REINSPECCION_OFICIO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if existente:
        assign_iniciador_domicilio_desde_origen(
            existente,
            getattr(actuacion, "domicilio_id", None),
            allow_update_existing=True,
        )
        return existente

    fecha_origen: date | None = oficio.fecha_oficio or expediente_respuesta.fecha_expediente
    if fecha_origen is None:
        raise ValueError("No se pudo determinar fecha_origen para iniciador derivado de oficio")

    domicilio_id = getattr(actuacion, "domicilio_id", None)
    if domicilio_id is None:
        raise ValueError("La actuación asociada al oficio no tiene domicilio para crear iniciador")

    domicilio_operativo_id = resolve_domicilio_operativo_para_iniciador(int(domicilio_id))

    created_by_user_id = _get_current_user_id()
    iniciador = IniciadorRuta(
        tipo_iniciador="REINSPECCION_OFICIO",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha_origen,
        anio=int(fecha_origen.year),
        mes=int(fecha_origen.month),
        domicilio_id=domicilio_operativo_id,
        prioridad=priority_for_tipo("REINSPECCION_OFICIO"),
        oficio_id=oficio.id,
        comprobacion_id=actuacion.comprobacion_id,
        actuacion_id=actuacion.id,
        created_by_user_id=created_by_user_id,
        observaciones=(
            f"Derivado automático desde oficio {oficio.numero_oficio}/{oficio.anio} "
            f"y expediente respuesta {expediente_respuesta.numero_expediente}/{expediente_respuesta.anio}"
        ),
    )
    return iniciador

