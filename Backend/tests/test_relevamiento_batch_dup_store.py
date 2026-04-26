"""Duplicados de ubicación+fecha en lote relevamientos (InMemoryBatchStore)."""

from app.domains.grid.services.batch_store import InMemoryBatchStore


def test_relevamiento_misma_ubicacion_misma_fecha_dos_filas_permitido():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|Y RIVADAVIA"

    assert store.upsert_relevamiento_dup(batch_id, "row-a", loc, "2026-03-01") is None
    assert store.upsert_relevamiento_dup(batch_id, "row-b", loc, "2026-03-01") is None


def test_relevamiento_misma_ubicacion_otra_fecha_duplicado():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|Y RIVADAVIA"

    assert store.upsert_relevamiento_dup(batch_id, "row-a", loc, "2026-03-01") is None
    other = store.upsert_relevamiento_dup(batch_id, "row-b", loc, "2026-03-15")
    assert other == "row-a"


def test_relevamiento_editar_fila_libera_conflicto():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MITRE|500"

    assert store.upsert_relevamiento_dup(batch_id, "r1", loc, "2026-01-10") is None
    assert store.upsert_relevamiento_dup(batch_id, "r2", loc, "2026-02-10") == "r1"
    # r2 falló y no debería haberse registrado (restore): r2 no está en índice
    store.clear_row_key(batch_id, "r2")
    assert store.upsert_relevamiento_dup(batch_id, "r2", loc, "2026-01-10") is None


def test_clear_row_key_relev_quita_indice():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "A|1"
    assert store.upsert_relevamiento_dup(batch_id, "x", loc, "2026-05-01") is None
    store.clear_row_key(batch_id, "x")
    assert store.upsert_relevamiento_dup(batch_id, "y", loc, "2026-06-01") is None


def test_actuaciones_clear_row_key_no_rompe():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="actuaciones")
    store.clear_row_key(batch_id, "no-existe")
