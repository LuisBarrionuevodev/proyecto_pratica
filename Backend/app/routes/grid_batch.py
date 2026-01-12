from __future__ import annotations

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.schemas.grid.batch import (
    StartBatchResponse,
    ValidateRowRequest,
    ValidateBatchRequest,
    ValidateBatchResponse,
)
from app.schemas.grid.errors import pydantic_errors_to_cell_map
from app.services.grid.batch_store import InMemoryBatchStore
from app.services.grid.validate_service import GridValidateService

bp = Blueprint("grid_batch", __name__, url_prefix="/grid")

store = InMemoryBatchStore()
svc = GridValidateService(store)


@bp.post("/batch/start")
def start_batch():
    batch_id = store.start_batch()
    resp = StartBatchResponse(batch_id=batch_id)
    return jsonify(resp.model_dump()), 200


@bp.post("/batch/validate-row")
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


@bp.post("/batch/validate-batch")
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
        row_id = item["row_id"]
        row = item["row"]
        results.append(svc.validate_row(req.batch_id, row_id, row))

    resp = ValidateBatchResponse(batch_id=req.batch_id, results=results)
    return jsonify(resp.model_dump()), 200
