"""
Agregaciones para GET /api/indicadores/pendientes.

Pendientes representa stock actual (cola planificable con geocode OK); no se filtra por período.
El endpoint puede recibir ``desde``/``hasta`` por contrato común de indicadores, pero se ignoran aquí.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import joinedload

from app.domains.geolocalizacion.geocode.services.map_operativo_service import (
    _borrador_item_exists_clause,
    _map_point_desde_iniciador_backlog,
)
from app.domains.indicadores.schemas.pendientes_out import DistritoPendientesItem, PendientesKpis
from app.models import Distrito, IniciadorRuta

_TIPOS_PENDIENTES_STOCK: tuple[str, ...] = (
    "RELEVAMIENTO",
    "REINSPECCION_OFICIO",
    "REINSPECCION_NOTIFICACION",
    "DENUNCIA",
)

_TIPOS_PENDIENTES_VISIBLES: frozenset[str] = frozenset(
    {
        "RELEVAMIENTO",
        "REINSPECCION_OFICIO",
        "REINSPECCION_NOTIFICACION",
    }
)

_SIN_DISTRITO_ID = 0
_SIN_DISTRITO_CODIGO = "SIN_DISTRITO"
_SIN_DISTRITO_NOMBRE = "Sin distrito"

_TOP_DISTRITOS_LIMIT = 15


@dataclass
class _DistritoBucket:
    relevamientos: int = 0
    reinspecciones_oficio: int = 0
    reinspecciones_notificacion: int = 0

    def add_tipo(self, tipo: str) -> None:
        if tipo == "RELEVAMIENTO":
            self.relevamientos += 1
        elif tipo == "REINSPECCION_OFICIO":
            self.reinspecciones_oficio += 1
        elif tipo == "REINSPECCION_NOTIFICACION":
            self.reinspecciones_notificacion += 1

    @property
    def total_visible(self) -> int:
        return self.relevamientos + self.reinspecciones_oficio + self.reinspecciones_notificacion


@dataclass
class PendientesStockAggregation:
    """Resultado de stock actual de pendientes (KPIs + ranking por distrito)."""

    kpis: PendientesKpis
    distritos: list[DistritoPendientesItem] = field(default_factory=list)
    scanned_count: int = 0
    mapped_count: int = 0


def _query_iniciadores_pendientes_stock() -> list[IniciadorRuta]:
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


def _distrito_meta(distrito_id: int) -> tuple[str, str]:
    if distrito_id == _SIN_DISTRITO_ID:
        return _SIN_DISTRITO_CODIGO, _SIN_DISTRITO_NOMBRE
    row = Distrito.query.filter(Distrito.id == distrito_id).first()
    if row is None:
        return str(distrito_id), f"Distrito {distrito_id}"
    codigo = str(row.codigo) if row.codigo is not None else str(distrito_id)
    return codigo, str(row.nombre)


def aggregate_pendientes_stock(
    *,
    distrito_id: Optional[int] = None,
    limit: int = _TOP_DISTRITOS_LIMIT,
) -> PendientesStockAggregation:
    """
    Cuenta stock actual de pendientes planificables (geocode OK) y agrupa por distrito.

    Parámetros:
        distrito_id: filtro opcional sobre domicilio efectivo con geocode OK.
        limit: máximo de filas en ranking por distrito.

    Retorno:
        KPIs globales (o del distrito filtrado) y tabla de distritos ordenada por total visible.

    Notas:
        ``inspector_id`` no aplica: la cola no tiene inspector asignado de forma confiable.
    """
    iniciadores = _query_iniciadores_pendientes_stock()

    counts = {
        "RELEVAMIENTO": 0,
        "REINSPECCION_OFICIO": 0,
        "REINSPECCION_NOTIFICACION": 0,
        "DENUNCIA": 0,
    }
    distritos_acc: dict[int, _DistritoBucket] = defaultdict(_DistritoBucket)
    mapped = 0

    for ini in iniciadores:
        pt = _map_point_desde_iniciador_backlog(ini, distrito_id=distrito_id)
        if pt is None:
            continue
        mapped += 1
        tipo = str(ini.tipo_iniciador)
        if tipo in counts:
            counts[tipo] += 1

        if tipo not in _TIPOS_PENDIENTES_VISIBLES:
            continue

        raw_dist_id = pt.get("distrito_id")
        dist_key = int(raw_dist_id) if raw_dist_id is not None else _SIN_DISTRITO_ID
        distritos_acc[dist_key].add_tipo(tipo)

    kpis = PendientesKpis(
        relevamientos_pendientes=counts["RELEVAMIENTO"],
        reinspecciones_oficio_pendientes=counts["REINSPECCION_OFICIO"],
        reinspecciones_notificacion_pendientes=counts["REINSPECCION_NOTIFICACION"],
        denuncias_pendientes=counts["DENUNCIA"],
        pendientes_geolocalizacion=0,
    )

    ranked = sorted(
        distritos_acc.items(),
        key=lambda item: (-item[1].total_visible, item[0]),
    )
    if distrito_id is not None:
        ranked = [(did, bucket) for did, bucket in ranked if did == distrito_id]

    distritos_out: list[DistritoPendientesItem] = []
    for did, bucket in ranked[:limit]:
        if bucket.total_visible <= 0:
            continue
        codigo, nombre = _distrito_meta(did)
        distritos_out.append(
            DistritoPendientesItem(
                distrito_id=did,
                distrito_codigo=codigo,
                distrito_nombre=nombre,
                relevamientos=bucket.relevamientos,
                denuncias=0,
                reinspecciones_oficio=bucket.reinspecciones_oficio,
                reinspecciones_notificacion=bucket.reinspecciones_notificacion,
                sin_geolocalizacion=0,
                total=bucket.total_visible,
            )
        )

    return PendientesStockAggregation(
        kpis=kpis,
        distritos=distritos_out,
        scanned_count=len(iniciadores),
        mapped_count=mapped,
    )
