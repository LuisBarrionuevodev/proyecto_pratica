"""Duplicados de establecimiento en lote relevamientos (InMemoryBatchStore), PR7.5/PR7.6."""

from app.domains.grid.services.batch_store import InMemoryBatchStore
from app.domains.grid.services.relevamiento_dup_key import build_relevamiento_establishment_key


def test_relevamiento_misma_ubicacion_esquina_varias_filas_permitido():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MAIPU|Y SALTA"
    est_a = build_relevamiento_establishment_key("Maipu", "y Salta", rubro_id=1, angulo_esquina="NE", es_esquina=True)
    est_b = build_relevamiento_establishment_key("Maipu", "y Salta", rubro_id=2, angulo_esquina="NE", es_esquina=True)
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-a", loc, True, est_a) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-b", loc, True, est_b) is None


def test_relevamiento_misma_ubicacion_numero_distinto_rubro_permitido():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|234"
    est_a = build_relevamiento_establishment_key("San Martin", "234", rubro_id=1, es_esquina=False)
    est_b = build_relevamiento_establishment_key("San Martin", "234", rubro_id=2, es_esquina=False)
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-a", loc, False, est_a) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-b", loc, False, est_b) is None


def test_relevamiento_misma_ubicacion_numero_mismo_establecimiento_duplicado():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|1009"
    est = build_relevamiento_establishment_key("San Martin", "1009", rubro_id=1, es_esquina=False)
    assert store.upsert_relevamiento_ubicacion(batch_id, "row-a", loc, False, est) is None
    other = store.upsert_relevamiento_ubicacion(batch_id, "row-b", loc, False, est)
    assert other == "row-a"


def test_clear_row_key_libera_clave_numero_para_otra_fila():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MITRE|500"
    est = build_relevamiento_establishment_key("Mitre", "500", rubro_id=1, es_esquina=False)
    assert store.upsert_relevamiento_ubicacion(batch_id, "r1", loc, False, est) is None
    store.clear_row_key(batch_id, "r1")
    assert store.upsert_relevamiento_ubicacion(batch_id, "r2", loc, False, est) is None


def test_clear_row_key_relev_quita_indice():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "A|1"
    est = build_relevamiento_establishment_key("A", "1", rubro_id=1, es_esquina=False)
    assert store.upsert_relevamiento_ubicacion(batch_id, "x", loc, False, est) is None
    store.clear_row_key(batch_id, "x")
    assert store.upsert_relevamiento_ubicacion(batch_id, "y", loc, False, est) is None


def test_misma_fila_cambia_de_numero_a_esquina_libera_indice():
    """Al editar la fila y pasar a ESQUINA, libera la clave NUMERO para otra fila."""
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "SAN MARTIN|1009"
    est_num = build_relevamiento_establishment_key("San Martin", "1009", rubro_id=1, es_esquina=False)
    est_esq = build_relevamiento_establishment_key("San Martin", "1009", rubro_id=1, angulo_esquina="NE", es_esquina=True)
    assert store.upsert_relevamiento_ubicacion(batch_id, "a", loc, False, est_num) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "a", loc, True, est_esq) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "b", loc, False, est_num) is None


def test_esquina_mismo_establecimiento_en_lote_bloquea():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="relevamientos")
    loc = "MAIPU|Y SALTA"
    est = build_relevamiento_establishment_key("Maipu", "y Salta", rubro_id=1, angulo_esquina="NE", es_esquina=True)
    assert store.upsert_relevamiento_ubicacion(batch_id, "x", loc, True, est) is None
    assert store.upsert_relevamiento_ubicacion(batch_id, "y", loc, True, est) == "x"


def test_actuaciones_clear_row_key_no_rompe():
    store = InMemoryBatchStore()
    batch_id = store.start_batch(kind="actuaciones")
    store.clear_row_key(batch_id, "no-existe")
