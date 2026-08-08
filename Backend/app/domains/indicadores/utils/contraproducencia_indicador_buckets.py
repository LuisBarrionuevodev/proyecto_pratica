"""
Buckets de contraproducencia para indicadores (Dashboard No realizadas / Productividad).

Agrupa valores persistidos o de catálogo en 5 categorías fijas de negocio.
``NO_HUBO`` y vacíos quedan excluidos (misma regla que ``/no-realizadas``).
"""

from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_contraproducencia import (
    STORED_CORRECTIVA_DIRECCION_INCORRECTA,
    STORED_CORRECTIVA_NO_ES_EL_RUBRO,
    STORED_NO_SE_RATIFICO,
    _loose_key,
    contraproducencia_es_familia_no_existe_local,
)
from app.domains.indicadores.services.indicadores_no_realizadas_queries import (
    is_contraproducencia_excluida_valor,
)

BUCKET_LOCAL_CERRADO = "local_cerrado"
BUCKET_NO_EXISTE = "no_existe"
BUCKET_NO_SE_RATIFICO = "no_se_ratifico"
BUCKET_CLIMA = "clima"
BUCKET_OTRAS = "otras"

BUCKET_ORDER: tuple[str, ...] = (
    BUCKET_LOCAL_CERRADO,
    BUCKET_NO_EXISTE,
    BUCKET_NO_SE_RATIFICO,
    BUCKET_CLIMA,
    BUCKET_OTRAS,
)

BUCKET_LABELS: dict[str, str] = {
    BUCKET_LOCAL_CERRADO: "Local cerrado",
    BUCKET_NO_EXISTE: "No existe",
    BUCKET_NO_SE_RATIFICO: "No se ratificó",
    BUCKET_CLIMA: "Clima",
    BUCKET_OTRAS: "Otras",
}

_PRODUCTIVIDAD_BUCKET_KEYS: tuple[str, ...] = (
    "inspecciones",
    "reinspecciones_oficio",
    "reinspecciones_notificacion",
    "denuncias",
)


def empty_contraproducencia_buckets() -> dict[str, int]:
    """Mapa bucket indicador → 0."""
    return {k: 0 for k in BUCKET_ORDER}


def classify_contraproducencia_indicador(raw: str | None) -> str | None:
    """
    Clasifica contraproducencia cruda en bucket de indicadores.

    Retorno:
        Clave de ``BUCKET_ORDER`` o ``None`` si se excluye (NO_HUBO / vacío).
    """
    if is_contraproducencia_excluida_valor(raw):
        return None
    key = _loose_key(str(raw))

    if key in (_loose_key("LOCAL CERRADO"), _loose_key("LOCAL_CERRADO")):
        return BUCKET_LOCAL_CERRADO

    if contraproducencia_es_familia_no_existe_local(str(raw)):
        return BUCKET_NO_EXISTE
    if key in (
        _loose_key(STORED_CORRECTIVA_NO_ES_EL_RUBRO),
        _loose_key(STORED_CORRECTIVA_DIRECCION_INCORRECTA),
        _loose_key("NO ES EL RUBRO"),
        _loose_key("DIRECCION INCORRECTA"),
        _loose_key("DIRECCIÓN INCORRECTA"),
    ):
        return BUCKET_NO_EXISTE

    if key in (
        _loose_key(STORED_NO_SE_RATIFICO),
        _loose_key("NO SE RATIFICO"),
        _loose_key("NO SE RATIFICÓ"),
    ):
        return BUCKET_NO_SE_RATIFICO

    if key == _loose_key("CLIMA"):
        return BUCKET_CLIMA

    return BUCKET_OTRAS


def merge_contraproducencia_counts(
    merged: dict[str, int],
    raw: str | None,
    count: int,
) -> None:
    """Suma ``count`` al bucket correspondiente si la contraproducencia cuenta."""
    bucket = classify_contraproducencia_indicador(raw)
    if bucket:
        merged[bucket] = merged.get(bucket, 0) + int(count)


def sum_productividad_buckets(buckets: dict[str, int]) -> int:
    """
    Suma única de los cuatro buckets de productividad por tipo operativo.

    No usar ``TIPO_INICIADOR_TO_PRODUCTIVIDAD_BUCKET.values()`` (tiene duplicados de oficio).
    """
    return sum(int(buckets.get(b, 0)) for b in _PRODUCTIVIDAD_BUCKET_KEYS)


def build_contraproducencias_resumen_items(
    counts: dict[str, int],
) -> list[dict[str, object]]:
    """
    Lista ordenada de buckets con etiqueta y cantidad (incluye ceros).

    Retorno:
        Lista de dicts serializables: bucket, label, cantidad.
    """
    return [
        {
            "bucket": key,
            "label": BUCKET_LABELS[key],
            "cantidad": int(counts.get(key, 0)),
        }
        for key in BUCKET_ORDER
    ]
