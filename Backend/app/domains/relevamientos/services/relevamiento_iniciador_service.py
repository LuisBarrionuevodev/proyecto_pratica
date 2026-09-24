from __future__ import annotations

from app.domains.rutas_trabajo.services.auth_service import validate_actor_user_id
from app.models import IniciadorRuta, Relevamiento
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    resolve_domicilio_operativo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)


def get_or_create_iniciador_from_relevamiento(
    relevamiento: Relevamiento,
    *,
    actor_user_id: int,
) -> IniciadorRuta:
    """
    Crea (o recupera) iniciador operativo para un relevamiento.

    Reglas:
    - tipo_iniciador = RELEVAMIENTO
    - estado_iniciador = PENDIENTE
    - idempotente para evitar duplicados activos.

    Parámetros:
        relevamiento: fila relevamiento origen.
        actor_user_id: usuario que audita la creación (obligatorio).

    Errores:
        ValueError: relevamiento incompleto o actor inválido.
    """
    existente = (
        IniciadorRuta.query.filter(
            IniciadorRuta.relevamiento_id == relevamiento.id,
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador.notin_(inactive_estados()),
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
    domicilio_operativo_id = resolve_domicilio_operativo_para_iniciador(int(relevamiento.domicilio_id))
    created_by_user_id = validate_actor_user_id(actor_user_id)
    return IniciadorRuta(
        tipo_iniciador="RELEVAMIENTO",
        estado_iniciador="PENDIENTE",
        fecha_origen=fecha_origen,
        anio=int(fecha_origen.year),
        mes=int(fecha_origen.month),
        domicilio_id=domicilio_operativo_id,
        prioridad=priority_for_tipo("RELEVAMIENTO"),
        relevamiento_id=relevamiento.id,
        created_by_user_id=created_by_user_id,
        observaciones=f"Derivado automático desde relevamiento {relevamiento.id}",
    )
