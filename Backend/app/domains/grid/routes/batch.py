from __future__ import annotations

from flask import request, jsonify, current_app
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.domains.grid.schemas.batch import (
    StartBatchRequest,
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
from app.domains.geolocalizacion.geocode.services.pipeline_service import (
    pipeline_post_commit,
)
from app.domains.catalogos.services.rubros_catalog_service import listar_rubros_catalogo
from app.models import (
    Inspector,
    Motivo,
    CatalogTipoActuacion,
    CatalogContraproducencia,
    CatalogMotivoComprobacion,
    JuzgadoCatalogo,
)  # catálogos para dropdowns

from app.security.rate_limiter import limit_grid_commit_batch, limit_grid_commit_row, limiter

from . import grid

store = InMemoryBatchStore()
svc = GridValidateService(store)


def _fetch_catalog(label: str, query_fn, map_fn):
    try:
        records = query_fn()
        payload = [map_fn(r) for r in records]
        return jsonify({"items": payload}), 200
    except SQLAlchemyError as e:
        current_app.logger.exception("DB error obteniendo catálogo %s", label)
        return (
            jsonify(
                {
                    "detail": f"Error de base de datos al obtener catálogo de {label}",
                    "error": str(e),
                }
            ),
            500,
        )
    except Exception as e:
        current_app.logger.exception("Error obteniendo catálogo %s", label)
        return (
            jsonify({"detail": f"Error al obtener catálogo de {label}", "error": str(e)}),
            500,
        )


@grid.post("/start")
@grid.post("/batch/start")  # compat: path anterior
def start_batch():
    try:
        data = request.get_json(silent=True) or {}
        req = StartBatchRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    kind = (req.kind or "actuaciones").strip().lower()
    batch_id = store.start_batch(kind=kind)
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

    batch = store.get(req.batch_id)
    resp = svc.validate_row(req.batch_id, req.row_id, req.row, batch.kind)
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
    batch = store.get(req.batch_id)
    for item in req.rows:
        results.append(svc.validate_row(req.batch_id, item.row_id, item.row, batch.kind))

    resp = ValidateBatchResponse(batch_id=req.batch_id, results=results)
    return jsonify(resp.model_dump()), 200


@grid.post("/commit-batch")
@limiter.limit(limit_grid_commit_batch)
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
    batch = store.get(req.batch_id)
    from app.domains.grid.services.registry import get_handler
    handler = get_handler(batch.kind)
    for item in req.rows:
        normalized = item.normalized or {}
        act_id = normalized.get("id")
        try:
            if act_id is None:
                act = handler.create_fn(normalized)
            else:
                act = handler.update_fn(int(act_id), normalized)

            try:
                domicilio_id = getattr(act, "domicilio_id", None)
                if domicilio_id:
                    pipeline_post_commit(int(domicilio_id))
            except Exception:
                pass

            results.append(
                CommitRowResponse(
                    batch_id=req.batch_id,
                    row_id=item.row_id,
                    ok=True,
                    errors={},
                    persisted=handler.presenter(act),
                )
            )
            store.clear_row_key(req.batch_id, item.row_id)
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
    return _fetch_catalog(
        "inspectores",
        lambda: Inspector.query.order_by(Inspector.nombre.asc()).all(),
        lambda i: {"id": i.id, "nombre": i.nombre, "legajo": i.legajo},
    )


@grid.get("/catalogs/motivos")
def list_motivos():
    """
    Devuelve catálogo de motivos para dropdowns del grid.

    Response: [{"id": int, "nombre": str}]
    """
    # Orden por nombre para UX consistente en frontend
    return _fetch_catalog(
        "motivos",
        lambda: Motivo.query.order_by(Motivo.nombre.asc()).all(),
        lambda m: {"id": m.id, "nombre": m.nombre},
    )


@grid.get("/catalogs/tipos")
def list_tipos_actuacion():
    """
    Devuelve catálogo de tipos de actuación para dropdowns del grid.
    """
    return _fetch_catalog(
        "tipos",
        lambda: CatalogTipoActuacion.query.order_by(CatalogTipoActuacion.nombre.asc()).all(),
        lambda t: {"id": t.id, "nombre": t.nombre},
    )


@grid.get("/catalogs/contraproducencias")
def list_contraproducencias():
    """
    Devuelve catálogo de contraproducencias para dropdowns del grid.
    """
    return _fetch_catalog(
        "contraproducencias",
        lambda: CatalogContraproducencia.query.order_by(CatalogContraproducencia.nombre.asc()).all(),
        lambda c: {"id": c.id, "nombre": c.nombre},
    )


@grid.get("/catalogs/motivos-comprobacion")
def list_motivos_comprobacion():
    """
    Devuelve catálogo de motivos de comprobación para dropdowns del grid.
    """
    return _fetch_catalog(
        "motivos-comprobacion",
        lambda: CatalogMotivoComprobacion.query.order_by(CatalogMotivoComprobacion.nombre.asc()).all(),
        lambda m: {"id": m.id, "nombre": m.nombre},
    )


@grid.get("/catalogs/rubros")
def list_rubros():
    """
    Devuelve catálogo de rubros para dropdowns del grid (delega en servicio STAB-8).

    Response: {"items": [{"id": int, "nombre": str, "activo": bool}]}
    """
    return jsonify({"items": listar_rubros_catalogo()}), 200


@grid.get("/catalogs/juzgados")
def list_juzgados():
    """
    Devuelve catálogo de juzgados para dropdowns.

    Response: [{"id": int, "codigo": str, "nombre": str}]
    """
    return _fetch_catalog(
        "juzgados",
        lambda: JuzgadoCatalogo.query.order_by(JuzgadoCatalogo.nombre.asc()).all(),
        lambda j: {"id": j.id, "codigo": j.codigo, "nombre": j.nombre},
    )


@grid.post("/commit-row")
@limiter.limit(limit_grid_commit_row)
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

    batch = store.get(req.batch_id)
    from app.domains.grid.services.registry import get_handler
    handler = get_handler(batch.kind)

    normalized = req.normalized or {}
    act_id = normalized.get("id")

    try:
        if act_id is None:
            act = handler.create_fn(normalized)
        else:
            act = handler.update_fn(int(act_id), normalized)

        try:
            domicilio_id = getattr(act, "domicilio_id", None)
            if domicilio_id:
                pipeline_post_commit(int(domicilio_id))
        except Exception:
            pass

        resp = CommitRowResponse(
            batch_id=req.batch_id,
            row_id=req.row_id,
            ok=True,
            errors={},
            persisted=handler.presenter(act),
        )
        store.clear_row_key(req.batch_id, req.row_id)
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
