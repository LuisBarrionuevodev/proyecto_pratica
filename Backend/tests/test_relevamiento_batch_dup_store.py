"""Duplicados de ubicación en lote relevamientos (InMemoryBatchStore), regla F3.2."""

from app.domains.grid.services.batch_store import InMemoryBatchStore


def test_relevamiento_misma_ubicacion_esquina_varias_filas_permitido():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MAIPU|Y SALTA"
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-a", loc, True) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-b", loc, True) is None


def test_relevamiento_misma_ubicacion_altura_distinta_fecha_duplicado_en_lote():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|1009"
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-a", loc, False) is None
    other = store.upsert_relevamiento_ubicacion(batch_id, "row-b", loc, False)
    assert other == "row-a"


def test_clear_row_key_libera_clave_altura_para_otra_fila():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MITRE|500"
    assert store.upsert_relevamiento_ubicacion(batch_id, "r1", loc, False) is None
    store.clear_row_key(batch_id, "r1")
    assert store.upsert_relevamiento_ubicacion(batch_id, "r2", loc, False) is None


def test_clear_row_key_relev_quita_indice():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "A|1"
    assert store.upsert_relevamiento_ubicacion(batch_id, "x", loc, False) is None
    store.clear_row_key(batch_id, "x")
    assert store.upsert_relevamiento_ubicacion(batch_id, "y", loc, False) is None


def test_misma_fila_cambia_de_altura_a_esquina_libera_indice():
    """Al editar la fila y pasar a ESQUINA, libera la clave de altura para otra fila."""
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|1009"
    assert store.upsert_relevamiento_ubicacion(batch_id, "a", loc, False) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "a", loc, True) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "b", loc, False) is None


def test_actuaciones_clear_row_key_no_rompe():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="actuaciones")
    store.clear_row_key(batch_id, "no-existe")
