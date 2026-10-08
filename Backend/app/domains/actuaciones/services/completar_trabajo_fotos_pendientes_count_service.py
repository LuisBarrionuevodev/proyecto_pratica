"""Conteo de trabajos con fotos pendientes para aviso Inspector (MEDIA.2D)."""

from __future__ import annotations

from app.domains.actuaciones.services.completar_trabajo_pendiente_filters import (
    ruta_item_pendiente_completar_trabajo_clause,
)
from app.domains.actuaciones.services.completar_trabajo_pendientes_query import (
    apply_completar_trabajo_inspector_scope,
    completar_trabajo_pendientes_ruta_item_base_query,
)
from app.models import RutaItem


def count_completar_trabajo_fotos_pendientes_inspector(
    *,
    inspector_id_effective: int,
) -> int:
    """
    Cuenta ítems FINALIZADos con fotos pendientes (flag o archivos PENDING), no finalizados por ahora.

    Parámetros:
        inspector_id_effective: scope Inspector autenticado.

    Retorno:
        Cantidad de trabajos distintos con fotos pendientes de subir.
    """
    base = completar_trabajo_pendientes_ruta_item_base_query().filter(
        ruta_item_pendiente_completar_trabajo_clause(),
        RutaItem.estado_ruta_item == "FINALIZADO",
    )
    base = apply_completar_trabajo_inspector_scope(base, inspector_id_effective)
    return int(base.count())
