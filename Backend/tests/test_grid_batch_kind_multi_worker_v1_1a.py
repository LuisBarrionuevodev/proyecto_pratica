"""
HOTFIX V1.1-OPER.1A — kind explícito en grid batch entre workers Gunicorn.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.domains.grid.services.batch_store import BatchKindMismatchError, InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService
from tests.relevamiento_test_helpers import get_or_create_test_relevador, get_test_rubro


def _raw_relevamiento_row(calle: str, numero: str, rubro: str, inspector: str) -> dict:
    return {
        "relevador": inspector,
        "calle": calle,
        "numero": numero,
        "rubro": rubro,
    }


def test_worker_b_validate_relevamientos_sin_fecha_tras_start_en_worker_a(app_ctx) -> None:
    from app.database import db

    rel = get_or_create_test_relevador()
    rub = get_test_rubro()
    store_a = InMemoryBatchStore()
    store_b = InMemoryBatchStore()
    svc_b = GridValidateService(store_b)

    batch_id = store_a.start_batch(kind="relevamientos")
    fixed = date(2026, 10, 2)
    store_b.ensure_for_request(batch_id, "relevamientos")
    st_b = store_b.get(batch_id)
    st_b.fecha_relevamiento_default = fixed

    try:
        calle = f"Oper1A-{uuid4().hex[:8]}"
        resp = svc_b.validate_row(
            batch_id,
            "r1",
            _raw_relevamiento_row(calle, "10", rub.nombre, rel.nombre),
            "relevamientos",
        )
        assert resp.ok is True, resp.errors
        assert resp.normalized is not None
        assert resp.normalized.get("fecha") == fixed.isoformat()
        assert "fecha_actuacion" not in (resp.errors or {})
        fecha_actuacion_msg = any(
            "actuación" in (v or "").lower() or "actuacion" in (v or "").lower()
            for v in (resp.errors or {}).values()
        )
        assert not fecha_actuacion_msg
    finally:
        db.session.rollback()


def test_worker_b_commit_usa_handler_relevamientos() -> None:
    from app.domains.grid.services.registry import get_handler
    from app.domains.relevamientos.services.create_service import crear_relevamiento_desde_payload

    store_a = InMemoryBatchStore()
    store_b = InMemoryBatchStore()
    batch_id = store_a.start_batch(kind="relevamientos")
    store_b.ensure_for_request(batch_id, "relevamientos")
    batch = store_b.get(batch_id)
    handler = get_handler(batch.kind)
    assert handler.kind == "relevamientos"
    assert handler.create_fn is crear_relevamiento_desde_payload


def test_kind_mismatch_local_actuaciones_request_relevamientos_409() -> None:
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="actuaciones")
    with pytest.raises(BatchKindMismatchError):
        store.ensure_for_request(batch_id, "relevamientos")


def test_get_no_recrea_batch_como_actuaciones() -> None:
    store = InMemoryBatchStore()
    missing = uuid4()
    with pytest.raises(KeyError):
        store.get(missing)


def test_api_validate_batch_kind_conflict_409(client, auth_headers) -> None:
    start = client.post("/grid/start", headers=auth_headers, json={"kind": "actuaciones"})
    assert start.status_code == 200
    batch_id = start.get_json()["batch_id"]
    resp = client.post(
        "/grid/validate-batch",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "kind": "relevamientos",
            "rows": [],
        },
    )
    assert resp.status_code == 409
    assert "detail" in resp.get_json()
