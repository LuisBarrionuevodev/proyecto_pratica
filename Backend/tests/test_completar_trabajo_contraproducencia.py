import pytest

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    ContrapBucket,
    STORED_NO_EXISTE_LOCAL,
    motivo_no_realizado_para_ruta_item,
    normalize_contraproducencia,
)


@pytest.mark.parametrize(
    ("raw", "stored", "bucket"),
    [
        (None, None, ContrapBucket.NONE),
        ("", None, ContrapBucket.NONE),
        ("  ", None, ContrapBucket.NONE),
        ("LOCAL CERRADO", "LOCAL CERRADO", ContrapBucket.REINGRESO_PRIORIDAD_ALTA),
        ("LOCAL_CERRADO", "LOCAL CERRADO", ContrapBucket.REINGRESO_PRIORIDAD_ALTA),
        ("CLIMA", "CLIMA", ContrapBucket.REINGRESO_PRIORIDAD_ALTA),
        ("NO EXISTE", STORED_NO_EXISTE_LOCAL, ContrapBucket.NO_EXISTE_LOCAL),
        ("NO EXISTE / NO COINCIDE RUBRO", STORED_NO_EXISTE_LOCAL, ContrapBucket.NO_EXISTE_LOCAL),
        ("NO EXISTE/NO ES EL RUBRO", STORED_NO_EXISTE_LOCAL, ContrapBucket.NO_EXISTE_LOCAL),
    ],
)
def test_normalize_contraproducencia(raw, stored, bucket) -> None:
    s, b = normalize_contraproducencia(raw)
    assert s == stored
    assert b == bucket


def test_motivo_no_existe() -> None:
    m = motivo_no_realizado_para_ruta_item(STORED_NO_EXISTE_LOCAL, ContrapBucket.NO_EXISTE_LOCAL)
    assert m == "NO_EXISTE_LOCAL"


def test_motivo_clima() -> None:
    m = motivo_no_realizado_para_ruta_item("CLIMA", ContrapBucket.REINGRESO_PRIORIDAD_ALTA)
    assert m == "INCLEMENCIA_TIEMPO"
