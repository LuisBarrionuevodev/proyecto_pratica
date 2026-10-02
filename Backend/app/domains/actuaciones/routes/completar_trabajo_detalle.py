from __future__ import annotations

from flask import jsonify
from flask_jwt_extended import jwt_required

from app.domains.actuaciones.services.completar_trabajo_detalle_service import (
    get_completar_trabajo_detalle,
)
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    RutaItemAccessError,
    assert_current_user_can_access_ruta_item,
)

from . import actuacion


@actuacion.get("/completar-trabajo/detalle/<int:ruta_item_id>")
@jwt_required()
def obtener_completar_trabajo_detalle(ruta_item_id: int):
    """
    Detalle para formulario Completar trabajo (fase 1).

    Incluye `row` (misma línea base que el listado), `inspectores_grupo` (solo lectura),
    `tipo_actuacion_esperado` según `tipo_iniciador`, y `ui_policy`.

    El cierre operativo sigue siendo POST `/completar-trabajo/cerrar/<ruta_item_id>`.

    Errors:
        404: ítem o actuación no encontrados
        400: estado no permitido para completar
    """
    try:
        assert_current_user_can_access_ruta_item(ruta_item_id)
        data = get_completar_trabajo_detalle(ruta_item_id=ruta_item_id)
        return jsonify(data), 200
    except RutaItemAccessError as e:
        return jsonify({"detail": str(e)}), e.status_code
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
