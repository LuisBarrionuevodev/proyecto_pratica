from __future__ import annotations

from datetime import date

from app.domains.rutas_trabajo.services.auth_service import validate_actor_user_id
from app.models import Actuaciones, Expediente, IniciadorRuta, Oficio
from app.domains.rutas_trabajo.services.iniciador_domicilio_service import (
    assign_iniciador_domicilio_desde_origen,
    resolve_domicilio_operativo_para_iniciador,
)
from app.domains.rutas_trabajo.services.iniciador_policy_service import (
    inactive_estados,
    priority_for_tipo,
)


def get_or_create_iniciador_from_oficio(
    *,
    actuacion: Actuaciones,
    oficio: Oficio,
    expediente_respuesta: Expediente,
    actor_user_id: int,
) -> IniciadorRuta:
    """
    Crea (o recupera) un iniciador derivado desde oficio en estado neutral pendiente.

    Parámetros:
        expediente_respuesta: expediente de **respuesta de oficio** (no el de envío de comprobación).
        actor_user_id: usuario que audita la creación (obligatorio).

    Reglas:
    - `tipo_iniciador` inicial: REINSPECCION_OFICIO.
    - Idempotente: no duplica iniciadores activos del mismo oficio.

    Errores:
        ValueError: datos incompletos o actor inválido.
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

    created_by_user_id = validate_actor_user_id(actor_user_id)
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
            f"(expediente respuesta {expediente_respuesta.numero_expediente})"
        ),
    )
    return iniciador
