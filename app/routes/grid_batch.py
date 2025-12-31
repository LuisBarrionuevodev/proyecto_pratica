from __future__ import annotations

from flask import Blueprint, request, jsonify

from app.schemas.grid.batch import StartBatchResponse, ValidateRowRequest
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
    data = request.get_json(force=True)
    req = ValidateRowRequest.model_validate(data)

    resp = svc.validate_row(req.batch_id, req.row_id, req.row)
    return jsonify(resp.model_dump()), 200


@bp.post("/batch/validate-batch")
def validate_batch():
    data = request.get_json(force=True)
    batch_id = data["batch_id"]
    rows = data.get("rows", [])

    results = []
    for item in rows:
        row_id = item["row_id"]
        row = item["row"]
        results.append(svc.validate_row(batch_id, row_id, row).model_dump())

    return jsonify({"batch_id": str(batch_id), "results": results}), 200
