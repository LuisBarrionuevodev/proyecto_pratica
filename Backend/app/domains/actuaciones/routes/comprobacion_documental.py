"""
GET/PATCH/DELETE documental de comprobación: expediente de envío y bloque oficio + expediente de respuesta.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from pydantic import ValidationError

from app.domains.actuaciones.schemas.comprobacion_documental_in import (
    ComprobacionExpedienteEnvioPatchIn,
    ComprobacionOficioBloquePatchIn,
)
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.actuaciones.services.comprobacion_documental_service import (
    delete_comprobacion_expediente_envio,
    delete_comprobacion_oficio_bloque,
    get_comprobacion_documental_for_actuacion,
    update_comprobacion_expediente_envio,
    update_comprobacion_oficio_bloque,
)

from . import actuacion


@actuacion.get("/<int:actuacion_id>/comprobacion/documental")
def get_comprobacion_documental(actuacion_id: int):
    """
    Devuelve expediente de envío, oficio y expediente de respuesta (si existen) y permisos de edición.

    Errores:
        404: actuación inexistente.
        400: sin comprobación.
    """
    try:
        payload = get_comprobacion_documental_for_actuacion(actuacion_id)
        return jsonify(payload), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@actuacion.patch("/<int:actuacion_id>/comprobacion/expediente-envio/<int:expediente_id>")
def patch_comprobacion_expediente_envio(actuacion_id: int, expediente_id: int):
    """
    Corrige número y fecha del expediente de envío de la comprobación.

    Body: ``numero_expediente``, ``fecha_expediente`` (YYYY-MM-DD).

    Errores:
        400: validación / bloqueo por iniciador.
        404: no encontrado.
        409: duplicado número/año.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        body = ComprobacionExpedienteEnvioPatchIn.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    try:
        out = update_comprobacion_expediente_envio(
            actuacion_id,
            expediente_id,
            numero_expediente=body.numero_expediente,
            fecha_expediente=body.fecha_expediente,
        )
        return jsonify({"ok": True, "item": out["item"], "expediente_id": out["expediente"].id}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409


@actuacion.delete("/<int:actuacion_id>/comprobacion/expediente-envio/<int:expediente_id>")
def delete_comprobacion_expediente_envio_route(actuacion_id: int, expediente_id: int):
    """
    Soft delete del expediente de envío (``ENVIO_ACTA`` sin oficio vinculado a la fila).

    Errores:
        400: bloqueo (iniciador, oficio ya cargado, etc.).
        404: no encontrado.
    """
    try:
        delete_comprobacion_expediente_envio(actuacion_id, expediente_id)
        return jsonify({"ok": True}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@actuacion.patch("/<int:actuacion_id>/comprobacion/oficios/<int:oficio_id>")
def patch_comprobacion_oficio_bloque(actuacion_id: int, oficio_id: int):
    """
    Actualiza oficio y expediente de respuesta (misma comprobación que la actuación).

    Body: ``numero_oficio``, ``fecha_oficio``, ``juzgado_id``, ``causa`` (opcional),
    ``numero_expediente_respuesta``, ``fecha_expediente_respuesta`` (opcional; si omite o difiere,
    se usa ``fecha_oficio``).

    Errores:
        400 / 404 / 409: mismos patrones que expediente envío.
    """
    data: Dict[str, Any] = request.get_json(silent=True) or {}
    try:
        body = ComprobacionOficioBloquePatchIn.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    try:
        out = update_comprobacion_oficio_bloque(
            actuacion_id,
            oficio_id,
            numero_oficio=body.numero_oficio,
            fecha_oficio=body.fecha_oficio,
            juzgado_id=body.juzgado_id,
            causa=body.causa,
            numero_expediente_respuesta=body.numero_expediente_respuesta,
            fecha_expediente_respuesta=body.fecha_expediente_respuesta,
        )
        return jsonify(
            {
                "ok": True,
                "oficio_item": out["oficio_item"],
                "expediente_respuesta_item": out["expediente_respuesta_item"],
                "oficio_id": out["oficio"].id,
            }
        ), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"detail": str(e)}), 409


@actuacion.delete("/<int:actuacion_id>/comprobacion/oficios/<int:oficio_id>")
def delete_comprobacion_oficio_bloque_route(actuacion_id: int, oficio_id: int):
    """
    Soft delete conjunto: expediente de respuesta del oficio y el oficio.

    Errores:
        400 / 404: mismos patrones que PATCH del bloque.
    """
    try:
        delete_comprobacion_oficio_bloque(actuacion_id, oficio_id)
        return jsonify({"ok": True}), 200
    except LookupError as e:
        return jsonify({"detail": str(e)}), 404
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
