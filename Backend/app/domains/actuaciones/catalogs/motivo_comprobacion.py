from __future__ import annotations

from app.models import CatalogMotivoComprobacion

_PLACEHOLDER_PENDIENTE = "PENDIENTE"


def es_placeholder_motivo_comprobacion(nombre: str | None) -> bool:
    """
    Indica si el texto es el placeholder legado `PENDIENTE` (previas).

    Parámetros:
        nombre: texto de `comprobacion.motivo` o equivalente.

    Returns:
        True si, tras strip, coincide con PENDIENTE (case-insensitive).
    """
    return (nombre or "").strip().upper() == _PLACEHOLDER_PENDIENTE


def get_catalog_motivo_comprobacion_exacto_o_none(
    nombre: str | None,
) -> CatalogMotivoComprobacion | None:
    """
    Lookup exacto (tras strip) en `catalog_motivo_comprobacion`.

    No infiere, no usa match laxo ni equivalencias. Vacío, NULL y PENDIENTE
    retornan None. 'Activo' = existe en el catálogo (la tabla no tiene flag
    `activo` ni `deleted_at`).

    Parámetros:
        nombre: texto a resolver contra `CatalogMotivoComprobacion.nombre`.

    Returns:
        Fila de catálogo o None si no hay coincidencia exacta usable.
    """
    s = (nombre or "").strip()
    if not s or es_placeholder_motivo_comprobacion(s):
        return None
    return CatalogMotivoComprobacion.query.filter_by(nombre=s).first()
