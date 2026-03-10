from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.domains.denuncias.schemas import (
    DenunciaCreateRequest,
    DenunciaGestionRowIn,
    DenunciasGestionFilters,
)
from app.domains.denuncias.services.denuncias_service import (
    actualizar_denuncia_gestion,
    crear_denuncia_con_iniciador,
    eliminar_denuncia_logicamente,
    listar_denuncias_gestion_operativa,
    listar_denuncias_gestion,
    listar_denuncias,
)
from app.domains.denuncias.services.operational_guard_service import DenunciaNoOperativaError
from app.shared.errors import pydantic_errors_to_cell_map

denuncias_api = Blueprint("denuncias_api", __name__)


@denuncias_api.post("/api/denuncias")
@jwt_required()
def create_denuncia():
    data = request.get_json(silent=True) or {}
    try:
        body = DenunciaCreateRequest.model_validate(data)
        denuncia, iniciador = crear_denuncia_con_iniciador(
            fecha=body.fecha,
            domicilio_id=body.domicilio_id,
            calle=body.calle,
            numero=body.numero,
            interseccion=body.interseccion,
            motivo=body.motivo,
        )
        payload = denuncia.to_dict()
        payload["iniciador_ruta_id"] = iniciador.id
        return jsonify(payload), 201
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except ValueError as e:
        msg = str(e)
        status = 401 if "no autorizado" in msg.lower() else 400
        return jsonify({"detail": msg}), status


@denuncias_api.get("/api/denuncias")
@jwt_required()
def list_denuncias():
    try:
        return jsonify(listar_denuncias()), 200
    except ValueError as e:
        return jsonify({"detail": str(e)}), 401


@denuncias_api.get("/api/denuncias/gestion")
@jwt_required()
def list_denuncias_gestion_route():
    try:
        raw_params = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw_params.items()}
        if "page" in params and params["page"]:
            params["page"] = int(params["page"])
        if "page_size" in params and params["page_size"]:
            params["page_size"] = int(params["page_size"])

        filters = DenunciasGestionFilters.model_validate(params)
        return jsonify(listar_denuncias_gestion(filters)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        msg = str(e)
        status = 401 if "no autorizado" in msg.lower() else 400
        return jsonify({"detail": msg}), status


@denuncias_api.get("/api/denuncias/gestion-operativa")
@jwt_required()
def list_denuncias_gestion_operativa_route():
    try:
        raw_params = request.args.to_dict()
        params = {k: (v if v else None) for k, v in raw_params.items()}
        if "page" in params and params["page"]:
            params["page"] = int(params["page"])
        if "page_size" in params and params["page_size"]:
            params["page_size"] = int(params["page_size"])

        filters = DenunciasGestionFilters.model_validate(params)
        return jsonify(listar_denuncias_gestion_operativa(filters)), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": e.errors()}), 422
    except ValueError as e:
        msg = str(e)
        status = 401 if "no autorizado" in msg.lower() else 400
        return jsonify({"detail": msg}), status


@denuncias_api.put("/api/denuncias/<int:denuncia_id>")
@jwt_required()
def update_denuncia_gestion_route(denuncia_id: int):
    data = request.get_json(silent=True) or {}
    try:
        data["id"] = denuncia_id
        row = DenunciaGestionRowIn.model_validate(data)
        updated = actualizar_denuncia_gestion(denuncia_id, row)
        return jsonify(updated), 200
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except DenunciaNoOperativaError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        msg = str(e)
        status = 401 if "no autorizado" in msg.lower() else 400
        return jsonify({"detail": msg}), status


@denuncias_api.delete("/api/denuncias/<int:denuncia_id>")
@jwt_required()
def delete_denuncia(denuncia_id: int):
    try:
        return jsonify(eliminar_denuncia_logicamente(denuncia_id)), 200
    except DenunciaNoOperativaError as e:
        return jsonify({"detail": str(e)}), 409
    except ValueError as e:
        msg = str(e)
        status = 401 if "no autorizado" in msg.lower() else 404
        return jsonify({"detail": msg}), status
