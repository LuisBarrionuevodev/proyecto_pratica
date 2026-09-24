"""Tests de clasificación de contraproducencias para indicadores."""

from __future__ import annotations

import pytest

from app.domains.indicadores.utils.contraproducencia_indicador_buckets import (
    BUCKET_CLIMA,
    BUCKET_LOCAL_CERRADO,
    BUCKET_NO_EXISTE,
    BUCKET_NO_SE_RATIFICO,
    BUCKET_OTRAS,
    classify_contraproducencia_indicador,
    empty_contraproducencia_buckets,
    merge_contraproducencia_counts,
    sum_productividad_buckets,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("LOCAL CERRADO", BUCKET_LOCAL_CERRADO),
        ("LOCAL_CERRADO", BUCKET_LOCAL_CERRADO),
        ("NO EXISTE/NO ES EL RUBRO", BUCKET_NO_EXISTE),
        ("NO_EXISTE_LOCAL", BUCKET_NO_EXISTE),
        ("NO ES EL RUBRO", BUCKET_NO_EXISTE),
        ("DIRECCION INCORRECTA", BUCKET_NO_EXISTE),
        ("NO SE RATIFICÓ", BUCKET_NO_SE_RATIFICO),
        ("NO SE RATIFICO", BUCKET_NO_SE_RATIFICO),
        ("CLIMA", BUCKET_CLIMA),
        ("ZONA ROJA", BUCKET_OTRAS),
        ("OTROS", BUCKET_OTRAS),
        ("NO PERMITE INSPECCION", BUCKET_OTRAS),
        ("NO PAGÓ TODAVÍA EL DECOMISO", BUCKET_OTRAS),
    ],
)
def test_classify_contraproducencia_indicador(raw: str, expected: str) -> None:
    assert classify_contraproducencia_indicador(raw) == expected


def test_no_hubo_excluido() -> None:
    assert classify_contraproducencia_indicador("NO_HUBO") is None
    assert classify_contraproducencia_indicador("NO HUBO") is None


def test_sum_productividad_buckets_sin_duplicar_oficio() -> None:
    buckets = {
        "inspecciones": 5,
        "reinspecciones_oficio": 2,
        "reinspecciones_notificacion": 0,
        "denuncias": 0,
    }
    assert sum_productividad_buckets(buckets) == 7


def test_merge_contraproducencia_counts() -> None:
    merged = empty_contraproducencia_buckets()
    merge_contraproducencia_counts(merged, "LOCAL CERRADO", 3)
    merge_contraproducencia_counts(merged, "CLIMA", 1)
    assert merged[BUCKET_LOCAL_CERRADO] == 3
    assert merged[BUCKET_CLIMA] == 1
    assert sum(merged.values()) == 4
