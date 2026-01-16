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
    CommitBatchRequest,  # nuevo: commit batch
    CommitBatchResponse,  # nuevo: commit batch
)
from app.shared.errors import pydantic_errors_to_cell_map
from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from app.domains.actuaciones.services.create_service import crear_actuacion_desde_payload
from app.domains.actuaciones.services.update_service import actualizar_actuacion
from app.domains.actuaciones.presenters.actuacion_presenters import actuacion_to_grid_row
from app.models import Inspector, Motivo, Rubro  # nuevo: catálogos para dropdowns

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


@grid.post("/commit-batch")
def commit_batch():
    """
    Persiste múltiples filas ya validadas (payload canon) en una sola request.

    Reglas:
    - Si normalized["id"] es None -> crea actuación
    - Si hay id -> actualiza actuación existente
    - Si falla una fila, continúa con las demás y devuelve ok=false en esa fila

    Errores de negocio (ValueError) se devuelven como ok=false con errors={"detail": "..."}.
    """
    try:
        data = request.get_json(force=True)
        req = CommitBatchRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    results = []
    for item in req.rows:
        normalized = item.normalized or {}
        act_id = normalized.get("id")
        try:
            if act_id is None:
                act = crear_actuacion_desde_payload(normalized)
            else:
                act = actualizar_actuacion(int(act_id), normalized)

            results.append(
                CommitRowResponse(
                    batch_id=req.batch_id,
                    row_id=item.row_id,
                    ok=True,
                    errors={},
                    persisted=actuacion_to_grid_row(act),
                )
            )
        except ValueError as e:
            results.append(
                CommitRowResponse(
                    batch_id=req.batch_id,
                    row_id=item.row_id,
                    ok=False,
                    errors={"detail": str(e)},
                    persisted=None,
                )
            )

    resp = CommitBatchResponse(batch_id=req.batch_id, results=results)
    return jsonify(resp.model_dump()), 200


@grid.get("/catalogs/inspectores")
def list_inspectores():
    """
    Devuelve catálogo de inspectores para dropdowns del grid.

    Response: [{"id": int, "nombre": str, "legajo": str}]
    """
    # Orden por nombre para UX consistente en frontend
    inspectores = Inspector.query.order_by(Inspector.nombre.asc()).all()
    payload = [{"id": i.id, "nombre": i.nombre, "legajo": i.legajo} for i in inspectores]
    return jsonify({"items": payload}), 200


@grid.get("/catalogs/motivos")
def list_motivos():
    """
    Devuelve catálogo de motivos para dropdowns del grid.

    Response: [{"id": int, "nombre": str}]
    """
    # Orden por nombre para UX consistente en frontend
    motivos = Motivo.query.order_by(Motivo.nombre.asc()).all()
    payload = [{"id": m.id, "nombre": m.nombre} for m in motivos]
    return jsonify({"items": payload}), 200


@grid.get("/catalogs/rubros")
def list_rubros():
    """
    Devuelve catálogo de rubros para dropdowns del grid.

    Response: [{"id": int, "nombre": str}]
    """
    # Orden por nombre para UX consistente en frontend
    rubros = Rubro.query.order_by(Rubro.nombre.asc()).all()
    payload = [{"id": r.id, "nombre": r.nombre} for r in rubros]
    return jsonify({"items": payload}), 200


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
