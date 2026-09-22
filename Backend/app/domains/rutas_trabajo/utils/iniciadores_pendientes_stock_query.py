"""Consulta de iniciadores PENDIENTE en cola planificable (compartida fuera del dashboard)."""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _borrador_item_exists_clause,
)
from app.models import IniciadorRuta

_TIPOS_PENDIENTES_STOCK: tuple[str, ...] = (
    "RELEVAMIENTO",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "DENUNCIA",
)


def query_iniciadores_pendientes_stock() -> list[IniciadorRuta]:
    """
    Iniciadores PENDIENTE en cola (sin ítem en ruta BORRADOR), sin filtro de ``fecha_origen``.

    Retorno:
        Lista de ``IniciadorRuta`` de los tipos operativos de cola.
    """
    return (
        IniciadorRuta.query.options(
            joinedload(IniciadorRuta.domicilio),
            joinedload(IniciadorRuta.relevamiento),
            joinedload(IniciadorRuta.denuncia),
            joinedload(IniciadorRuta.actuacion),
        )
        .filter(
            IniciadorRuta.deleted_at.is_(None),
            IniciadorRuta.estado_iniciador == "PENDIENTE",
            IniciadorRuta.tipo_iniciador.in_(_TIPOS_PENDIENTES_STOCK),
            ~_borrador_item_exists_clause(),
        )
        .all()
    )
