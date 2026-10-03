from __future__ import annotations

from datetime import date

from app.domains.actuaciones.presenters.completar_trabajo_presenters import ruta_item_completar_trabajo_to_row
from app.domains.actuaciones.services.completar_trabajo_pendientes_query import (
    apply_completar_trabajo_inspector_scope,
    completar_trabajo_pendientes_ruta_item_base_query,
)
from app.models import RutaItem, RutaTrabajo


def list_completar_trabajo_pendientes(
    *,
    fecha: date,
    page: int,
    per_page: int,
    inspector_id_effective: int | None = None,
) -> tuple[list[dict], dict]:
    """
    Lista ítems de ruta publicada con actuación mínima pendientes de completar para una fecha.

    Criterio:
    - RutaItem activo, EN_PROCESO, con actuacion_id.
    - RutaTrabajo PUBLICADA.
    - RutaTrabajo.fecha = fecha (día operativo de la ruta; al publicar coincide con Actuaciones.fecha).

    Parámetros:
        fecha: día a listar.
        page: página (1-based).
        per_page: cantidad por página.
        inspector_id_effective: scope Inspector (INSPECTOR.2); None = vista global.

    Retorno:
        Tupla (lista de dicts presenter, meta con total/page/per_page/fecha).

    Errores:
        Ninguno; lista vacía si no hay coincidencias.
    """
    base = completar_trabajo_pendientes_ruta_item_base_query().filter(
        RutaItem.estado_ruta_item == "EN_PROCESO",
        RutaTrabajo.fecha == fecha,
    )
    base = apply_completar_trabajo_inspector_scope(base, inspector_id_effective).order_by(
        RutaItem.id.asc()
    )

    total = base.count()
    offset = (page - 1) * per_page
    items = base.offset(offset).limit(per_page).all()

    rows = [ruta_item_completar_trabajo_to_row(it) for it in items]
    meta = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "fecha": fecha.isoformat(),
    }
    return rows, meta
