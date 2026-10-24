"""Clave de idempotencia en vínculos RutaItem ↔ Archivo (SHA por categoría)."""

from __future__ import annotations

from app.models import RutaItemArchivo


def release_content_sha256_idempotency_key(link: RutaItemArchivo) -> None:
    """
    Libera el índice único (ruta_item, categoría, content_sha256) sin borrar el vínculo.

    Parámetros:
        link: fila histórica cuyo archivo ya no debe bloquear reintentos (p. ej. DELETED).
    """
    link.content_sha256 = None
