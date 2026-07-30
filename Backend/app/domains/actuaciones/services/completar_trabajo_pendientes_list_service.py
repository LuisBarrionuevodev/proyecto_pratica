from __future__ import annotations

from datetime import date

from sqlalchemy.orm import joinedload, selectinload

from app.models import Actuaciones, Domicilio, IniciadorRuta, Relevamiento, RutaGrupo, RutaGrupoInspector, RutaItem, RutaTrabajo

from app.domains.actuaciones.presenters.completar_trabajo_presenters import ruta_item_completar_trabajo_to_row


def list_completar_trabajo_pendientes(
    *,
    fecha: date,
    page: int,
    per_page: int,
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

    Retorno:
        Tupla (lista de dicts presenter, meta con total/page/per_page/fecha).

    Errores:
        Ninguno; lista vacía si no hay coincidencias.

    Nota: el presenter de cada ítem no expone campos de previas; no forman parte del módulo
    Completar trabajo en esta etapa.

    Para agregados por rango de fechas sin paginar, ver
    `GET /actuaciones/completar-trabajo/pendientes/resumen` y
    `list_completar_trabajo_pendientes_resumen_por_dia`.
    """
    base = (
        RutaItem.query.join(Actuaciones, RutaItem.actuacion_id == Actuaciones.id)
        .join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "EN_PROCESO",
            RutaItem.actuacion_id.isnot(None),
            RutaTrabajo.estado_ruta == "PUBLICADA",
            RutaTrabajo.fecha == fecha,
        )
        .options(
            joinedload(RutaItem.actuacion).options(
                joinedload(Actuaciones.orden_trabajo),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
                joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
                selectinload(Actuaciones.inspector),
            ),
            joinedload(RutaItem.iniciador_ruta).options(
                joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
                joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
                joinedload(IniciadorRuta.notificacion),
            ),
            joinedload(RutaItem.ruta_grupo)
            .selectinload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
        .order_by(RutaItem.id.asc())
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
