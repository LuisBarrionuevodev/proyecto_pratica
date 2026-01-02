from app.services.grid.batch_store import InMemoryBatchStore
from app.services.grid.validate_service import GridValidateService


def test_validate_row_ok_minimo():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "tipo_actuacion": "INSPECCION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is True
    assert resp.errors == {}
    assert resp.normalized is not None
    assert resp.normalized["tipo_actuacion"] == "INSPECCION"


def test_fila_vacia_con_ot_exige_contraproducencia():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        # fila "vacía" (solo OT+fecha) => exige contraproducencia
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is False
    assert "contraproducencia" in resp.errors


def test_reinspeccion_exige_notificacion_previa():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "tipo_actuacion": "REINSPECCION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",
        # falta notificacion_previa_num
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is False
    assert "notificacion_previa_num" in resp.errors


def test_ratificacion_clausura_exige_comprobacion_previa():
    store = InMemoryBatchStore()
    svc = GridValidateService(store)
    batch_id = store.start_batch()

    raw = {
        "tipo_actuacion": "RATIFICACION DE CLAUSURA",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "2025-12-31",
        # falta comprobacion_previa_num
    }

    resp = svc.validate_row(batch_id=batch_id, row_id="row-1", raw_row=raw)
    assert resp.ok is False
    assert "comprobacion_previa_num" in resp.errors


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
        "tipo_actuacion": "REINSPECCION",
        "orden_trabajo_numero": "123",
        "fecha_actuacion": "31/12/2025",  # misma fecha, distinto formato
        "notificacion_previa_num": "000111",  # para pasar regla de REINSPECCION
    }

    r1 = svc.validate_row(batch_id, "row-1", raw1)
    r2 = svc.validate_row(batch_id, "row-2", raw2)

    assert r1.ok is True
    assert r2.ok is False
    assert "_row" in r2.errors
