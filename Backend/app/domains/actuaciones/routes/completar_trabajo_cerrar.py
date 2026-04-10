from __future__ import annotations

from typing import Any

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import cerrar_completar_trabajo_por_ruta_item
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id_or_fallback
from app.shared.errors import pydantic_errors_to_cell_map
from app.security.rate_limiter import limit_completar_trabajo_cerrar, limiter

from . import actuacion


@actuacion.post("/completar-trabajo/cerrar/<int:ruta_item_id>")
@limiter.limit(limit_completar_trabajo_cerrar)
def cerrar_completar_trabajo(ruta_item_id: int):
    """
    **Completar trabajo** — cierre operativo (actuación + ruta_item + iniciador) en una transacción.

    Body: PR2 + actas del día permitidas (inspección, notificación+motivos, comprobación, clausura,
    decomiso+kilos) y domicilio/contrib extendido. Oficio y expediente administrativo solo por
    **Esperando oficio** / **Esperando expediente**. Con contraproducencia no se permiten actas.

    Recurso lógico: la **actuación**; ancla HTTP: **ruta_item_id** (ítem EN_PROCESO que se cierra).
    `tipo_actuacion` y `contraproducencia` se validan contra catálogo DB; si se envía tipo, debe coincidir
    con el esperado para `tipo_iniciador`.

    - Sin contraproducencia (o vacía): visita realizada → RutaItem FINALIZADO, iniciador CUMPLIDO.
    - Con contraproducencia: según normalización → reingreso PENDIENTE prioridad alta o cierre CERRADO_NO_EXISTE_LOCAL.

    Returns:
        { "item": <fila presenter> }

    Errors:
        400: validación de negocio
        404: ítem no encontrado
        422: Pydantic
    """
    data: dict[str, Any] = request.get_json(silent=True) or {}
    try:
        payload = CompletarTrabajoCierreCompletoIn.model_validate(data)
        user_id = get_current_user_id_or_fallback()
        row = cerrar_completar_trabajo_por_ruta_item(
            ruta_item_id=ruta_item_id,
            payload=payload,
            ejecutado_por_user_id=user_id,
        )
        return jsonify({"item": row}), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
