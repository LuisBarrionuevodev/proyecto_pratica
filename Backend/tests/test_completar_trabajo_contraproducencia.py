import pytest

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    CATALOG_CONTRAPRODUCCION_NO_EXISTE_CANONICAL,
    ContrapBucket,
    STORED_CORRECTIVA_DIRECCION_INCORRECTA,
    STORED_CORRECTIVA_NO_ES_EL_RUBRO,
    STORED_NO_EXISTE_LOCAL,
    STORED_NO_PERMITE_INSPECCION,
    map_contraproducencia_alias_to_catalog_nombre,
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
        ("NO PERMITE INSPECCION", STORED_NO_PERMITE_INSPECCION, ContrapBucket.NO_PERMITE_INSPECCION),
        ("NO_PERMITE_INSPECCION", STORED_NO_PERMITE_INSPECCION, ContrapBucket.NO_PERMITE_INSPECCION),
        ("NO ES EL RUBRO", "NO ES EL RUBRO", ContrapBucket.REINGRESO_PRIORIDAD_ALTA),
        ("DIRECCIÓN INCORRECTA", "DIRECCION INCORRECTA", ContrapBucket.REINGRESO_PRIORIDAD_ALTA),
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


def test_motivo_correctivas_reingreso() -> None:
    m = motivo_no_realizado_para_ruta_item("NO ES EL RUBRO", ContrapBucket.REINGRESO_PRIORIDAD_ALTA)
    assert m == "OTRO"
    m2 = motivo_no_realizado_para_ruta_item(
        STORED_CORRECTIVA_DIRECCION_INCORRECTA, ContrapBucket.REINGRESO_PRIORIDAD_ALTA
    )
    assert m2 == "OTRO"


def test_motivo_no_permite_inspeccion() -> None:
    m = motivo_no_realizado_para_ruta_item(
        STORED_NO_PERMITE_INSPECCION, ContrapBucket.NO_PERMITE_INSPECCION
    )
    assert m == "OTRO"


@pytest.mark.parametrize(
    ("raw", "expected_catalog"),
    [
        ("NO EXISTE", CATALOG_CONTRAPRODUCCION_NO_EXISTE_CANONICAL),
        ("NO EXISTE / NO COINCIDE RUBRO", CATALOG_CONTRAPRODUCCION_NO_EXISTE_CANONICAL),
        ("LOCAL CERRADO", "LOCAL CERRADO"),
        ("NO_PERMITE_INSPECCION", STORED_NO_PERMITE_INSPECCION),
        ("DIRECCIÓN INCORRECTA", STORED_CORRECTIVA_DIRECCION_INCORRECTA),
        ("NO ES EL RUBRO", STORED_CORRECTIVA_NO_ES_EL_RUBRO),
    ],
)
def test_map_contraproducencia_alias_to_catalog_nombre(raw, expected_catalog) -> None:
    assert map_contraproducencia_alias_to_catalog_nombre(raw) == expected_catalog
