from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import Domicilio, IniciadorRuta, Relevamiento, RutaItem, RutaTrabajo


def get_iniciadores_pendientes_para_ruta(
    *,
    ruta_id: int,
    tipo: str | None,
    prioridad: int | None,
    distrito: int | None,
    q: str | None,
    turno_sugerido: str | None,
    page: int,
    per_page: int,
) -> tuple[list[IniciadorRuta], int]:
    """
    Lista iniciadores planificables para una ruta en BORRADOR.

    Reglas:
    - ruta debe existir y estar en BORRADOR.
    - solo iniciadores PENDIENTE y no soft-deleted.
    - excluye iniciadores ya tomados por RutaItem no eliminado de rutas activas.
    - para slice 1, ruta activa = BORRADOR.

    Returns:
    - tupla (items, total)

    Raises:
    - LookupError: si ruta no existe.
    - RuntimeError: si ruta no está en BORRADOR.
    """
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("La ruta debe estar en BORRADOR para listar iniciadores pendientes")

    query = (
        IniciadorRuta.query.join(Domicilio, Domicilio.id == IniciadorRuta.domicilio_id)
        .options(
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.calle_catalogo),
            joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.distrito),
            joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
        )
        .filter(
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.deleted_at.is_(None),
            ~IniciadorRuta.ruta_items.any(
                (RutaItem.deleted_at.is_(None))
                & (RutaItem.ruta_trabajo.has(RutaTrabajo.estado_ruta == "BORRADOR"))
            ),
        )
    )

    if tipo:
        query = query.filter(IniciadorRuta.tipo_iniciador == tipo)
    if prioridad is not None:
        query = query.filter(IniciadorRuta.prioridad == prioridad)
    if distrito is not None:
        query = query.filter(Domicilio.distrito_id == distrito)
    if turno_sugerido:
        query = query.filter(IniciadorRuta.turno_sugerido == turno_sugerido)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                Domicilio.calle.ilike(term),
                Domicilio.numero.ilike(term),
                IniciadorRuta.observaciones.ilike(term),
            )
        )

    total = query.count()
    items = (
        query.order_by(
            IniciadorRuta.fecha_origen.asc(),
            IniciadorRuta.prioridad.asc(),
            IniciadorRuta.id.asc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return items, total
