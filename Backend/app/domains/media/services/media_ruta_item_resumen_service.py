"""Resumen de evidencias por RutaItem (READY / PENDING) para Completar trabajo."""

from __future__ import annotations

from app.database import db
from app.domains.media.constants import (
    CATEGORIA_FOTO_ACTA,
    CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
    CATEGORIA_FOTO_INSPECCION,
)
from app.integrations.media_storage.config import load_media_storage_config, max_archivos_por_categoria
from app.models import Archivo, RutaItemArchivo


def _counts_for_categoria(ruta_item_id: int, categoria: str) -> tuple[int, int]:
    rows = (
        db.session.query(Archivo.status, db.func.count(Archivo.id))
        .join(RutaItemArchivo, RutaItemArchivo.archivo_id == Archivo.id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            RutaItemArchivo.categoria == categoria,
            Archivo.deleted_at.is_(None),
            Archivo.status.in_(("PENDING", "READY")),
        )
        .group_by(Archivo.status)
        .all()
    )
    ready = pending = 0
    for status, cnt in rows:
        if status == "READY":
            ready = int(cnt)
        elif status == "PENDING":
            pending = int(cnt)
    return ready, pending


def build_media_resumen_ruta_item(ruta_item_id: int) -> dict[str, object]:
    """
    Conteos por categoría y flags de evidencia pendiente.

    Parámetros:
        ruta_item_id: ítem ancla.

    Retorno:
        Dict serializable (sin URLs).
    """
    cfg = load_media_storage_config()
    cat_specs = (
        ("foto_acta", CATEGORIA_FOTO_ACTA),
        ("foto_documentacion_local", CATEGORIA_FOTO_DOCUMENTACION_LOCAL),
        ("foto_inspeccion", CATEGORIA_FOTO_INSPECCION),
    )
    out_cats: dict[str, dict[str, int]] = {}
    total_pending = 0
    for key, cat in cat_specs:
        ready, pending = _counts_for_categoria(ruta_item_id, cat)
        max_n = max_archivos_por_categoria(cfg, cat)
        out_cats[key] = {
            "ready": ready,
            "pending": pending,
            "max": max_n,
            "pendientes": max(0, max_n - ready),
        }
        total_pending += pending
    return {
        **out_cats,
        "tiene_evidencias_pendientes": total_pending > 0,
        "evidencias_pendientes_total": total_pending,
    }


def ruta_item_tiene_archivos_pending(ruta_item_id: int) -> bool:
    """True si hay al menos un Archivo PENDING activo vinculado al ítem."""
    n = (
        db.session.query(Archivo.id)
        .join(RutaItemArchivo, RutaItemArchivo.archivo_id == Archivo.id)
        .filter(
            RutaItemArchivo.ruta_item_id == int(ruta_item_id),
            Archivo.status == "PENDING",
            Archivo.deleted_at.is_(None),
        )
        .limit(1)
        .count()
    )
    return n > 0
