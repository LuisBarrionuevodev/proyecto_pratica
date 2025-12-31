from app.services.grid.batch_store import InMemoryBatchStore
from app.services.grid.validate_service import GridValidateService


def test_validate_row_ok():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "tipo_actuacion": "NOTIFICACION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        "acta_notificacion_num": "N-55",
        "notificacion_motivo_1": "Falta rotulado",
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is True
    assert resp.errors == {}
    assert resp.normalized is not None


def test_validate_row_errors_by_cell_notificacion():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "tipo_actuacion": "NOTIFICACION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        # faltan acta_notificacion_num y motivos
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is False
    # errores por celda
    assert "acta_notificacion_num" in resp.errors or "notificacion_motivo_1" in resp.errors


def test_duplicate_ot_fecha_in_batch():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw1 = {
        "tipo_actuacion": "INSPECCION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "2025-12-31",
    }

    raw2 = {
        "tipo_actuacion": "COMPROBACION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        "acta_comprobacion_num": "C-10",
        "comprobacion_motivo": "Control",
    }

    r1 = svc.validate_row(batch_id, "row-1", raw1)
    r2 = svc.validate_row(batch_id, "row-2", raw2)

    assert r1.ok is True
    assert r2.ok is False
    assert "_row" in r2.errors

