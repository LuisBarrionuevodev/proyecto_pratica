from __future__ import annotations

from flask_jwt_extended import get_jwt_identity

from app.models import IniciadorRuta, Relevamiento, User


def _get_current_user_id() -> int:
    """
    Resuelve user_id autenticado para auditoría.

    Compatibilidad:
    - Si no hay contexto JWT (ruta legacy), usa un usuario activo como fallback.
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

    fallback_user = User.query.filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
    if fallback_user:
        return int(fallback_user.id)
    raise ValueError("No hay usuario activo para registrar created_by_user_id")


def get_or_create_iniciador_from_relevamiento(relevamiento: Relevamiento) -> IniciadorRuta:
    """
    Crea (o recupera) iniciador operativo para un relevamiento.

    Reglas:
    - tipo_iniciador = RELEVAMIENTO
    - estado_iniciador = PENDIENTE
    - idempotente para evitar duplicados activos.
    """
    existente = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == relevamiento.id,
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(("ANULADO", "CERRADO", "CERRADO_NO_EXISTE_LOCAL")),
        )
        .order_by(IniciadorRuta.id.desc())
        .first()
    )
    if existente:
        return existente

    if not relevamiento.fecha:
        raise ValueError("El relevamiento no tiene fecha para crear iniciador")
    if not relevamiento.domicilio_id:
        raise ValueError("El relevamiento no tiene domicilio para crear iniciador")

    fecha_origen = relevamiento.fecha
    created_by_user_id = _get_current_user_id()
    return IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha_origen,
        anio=int(fecha_origen.year),
        mes=int(fecha_origen.month),
        domicilio_id=int(relevamiento.domicilio_id),
        relevamiento_id=relevamiento.id,
        created_by_user_id=created_by_user_id,
        observaciones=f"Derivado automático desde relevamiento {relevamiento.id}",
    )

