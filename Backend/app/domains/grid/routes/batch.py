from __future__ import annotations

from flask import request, jsonify
from pydantic import ValidationError

from app.domains.grid.schemas.batch import (
    StartBatchResponse,
    ValidateRowRequest,
    ValidateBatchRequest,
    ValidateBatchResponse,
    CommitRowRequest,
    CommitRowResponse,
)
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row

from . import grid

store = InMemoryBatchStore()
svc = GridValidateService(store)


@grid.post("/start")
@grid.post("/batch/start")  # compat: path anterior
def start_batch():
    batch_id = store.start_batch()
    resp = StartBatchResponse(batch_id=batch_id)
    return jsonify(resp.model_dump()), 200


@grid.post("/validate-row")
@grid.post("/batch/validate-row")  # compat: path anterior
def validate_row():
    try:
        data = request.get_json(force=True)
        req = ValidateRowRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    resp = svc.validate_row(req.batch_id, req.row_id, req.row)
    return jsonify(resp.model_dump()), 200


@grid.post("/validate-batch")
@grid.post("/batch/validate-batch")  # compat: path anterior
def validate_batch():
    try:
        data = request.get_json(force=True)
        req = ValidateBatchRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    results = []
    for item in req.rows:
        results.append(svc.validate_row(req.batch_id, item.row_id, item.row))

    resp = ValidateBatchResponse(batch_id=req.batch_id, results=results)
    return jsonify(resp.model_dump()), 200


@grid.post("/commit-row")
def commit_row():
    """
    Persiste una fila ya validada/mapeada (payload canon) sin revalidar su contenido.

    Reglas:
    - Si normalized["id"] es None -> crea actuación
    - Si hay id -> actualiza actuación existente

    Errores de negocio (ValueError) se devuelven como ok=false con errors={"detail": "..."}.
    """
    try:
        data = request.get_json(force=True)
        req = CommitRowRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    normalized = req.normalized or {}
    act_id = normalized.get("id")

    try:
        if act_id is None:
            act = crear_actuacion_desde_payload(normalized)
        else:
            act = actualizar_actuacion(int(act_id), normalized)

        resp = CommitRowResponse(
            batch_id=req.batch_id,
            row_id=req.row_id,
            ok=True,
            errors={},
            persisted=actuacion_to_grid_row(act),
        )
        return jsonify(resp.model_dump()), 200
    except ValueError as e:
        resp = CommitRowResponse(
            batch_id=req.batch_id,
            row_id=req.row_id,
            ok=False,
            errors={"detail": str(e)},
            persisted=None,
        )
        return jsonify(resp.model_dump()), 200
