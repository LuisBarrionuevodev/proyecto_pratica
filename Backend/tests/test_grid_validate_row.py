"""Validación de filas del grid de actuaciones (GridValidateService, sin DB en reglas de lote)."""

from __future__ import annotations

from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.validate_service import GridValidateService

KIND = "actuaciones"


def _fila_inspeccion_ok() -> dict:
    return {
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "tipo_actuacion": "INSPECCION",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
        "acta_inspeccion_num": "000042",
    }


def test_validate_row_ok_minimo(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind=KIND)

    with app.app_context():
        resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=_fila_inspeccion_ok(), kind=KIND)

    assert resp.ok is True
    assert resp.errors == {}
    assert resp.normalized is not None
    assert resp.normalized["tipo_actuacion"] == "INSPECCION"


def test_fila_vacia_con_ot_exige_contraproducencia(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind=KIND)

    raw = {
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
    }

    with app.app_context():
        resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw, kind=KIND)

    assert resp.ok is False
    assert "Contraproducencia" in resp.errors


def test_reinspeccion_exige_notificacion_previa(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind=KIND)

    raw = {
        "tipo_actuacion": "REINSPECCION",
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "31/12/2025",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
    }

    with app.app_context():
        resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw, kind=KIND)

    assert resp.ok is False
    assert "notificacion_previa_num" in resp.errors


def test_ratificacion_clausura_exige_comprobacion_previa(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind=KIND)

    raw = {
        "tipo_actuacion": "RATIFICACION DE CLAUSURA",
        "orden_trabajo_numero": "123456",
        "fecha_actuacion": "2025-12-31",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
    }

    with app.app_context():
        resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw, kind=KIND)

    assert resp.ok is False
    assert "comprobacion_previa_num" in resp.errors


def test_duplicate_ot_fecha_in_batch(app) -> None:
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch(kind=KIND)

    raw1 = {
        **_fila_inspeccion_ok(),
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "2025-12-31",
    }

    raw2 = {
        "tipo_actuacion": "REINSPECCION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        "notificacion_previa_num": "000111",
        "calle": "San Martín",
        "numero": "100",
        "rubro_nombre": "Bar",
        "doc_nro": "30123456",
        "inspector1": "Inspector Uno",
    }

    with app.app_context():
        r1 = svc.validate_row(batch_id, "row-1", raw1, KIND)
        r2 = svc.validate_row(batch_id, "row-2", raw2, KIND)

    assert r1.ok is True
    assert r2.ok is False
    assert "_row" in r2.errors
