"""
Contexto de cierre (último ruta_item FINALIZADO) para filas de bandeja Procesados.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case
from sqlalchemy.orm import joinedload

from app.models import Actuaciones, RutaItem


@dataclass(frozen=True)
class ProcesadosCierreContext:
    """Datos del último cierre operativo del iniciador."""

    motivo_no_realizado: str | None
    contraproducencia: str | None
    fecha_cierre: datetime | None


def fetch_ultimo_cierre_por_iniciador(iniciador_ids: list[int]) -> dict[int, ProcesadosCierreContext]:
    """
    Por cada iniciador, toma el ``RutaItem`` FINALIZADO más reciente (``ejecutado_at``, luego ``id``).

    Parámetros:
        iniciador_ids: ids de iniciador_ruta en la página actual.

    Retorno:
        Mapa iniciador_id → contexto de cierre (puede faltar si no hubo ítem finalizado).
    """
    if not iniciador_ids:
        return {}
    uniq_ids = sorted({int(x) for x in iniciador_ids if x})
    items = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id.in_(uniq_ids),
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item == "FINALIZADO",
        )
        .options(joinedload(RutaItem.actuacion))
        .order_by(
            case((RutaItem.ejecutado_at.is_(None), 1), else_=0),
            RutaItem.ejecutado_at.desc(),
            RutaItem.id.desc(),
        )
        .all()
    )
    out: dict[int, ProcesadosCierreContext] = {}
    for item in items:
        iid = int(item.iniciador_ruta_id)
        if iid in out:
            continue
        act: Actuaciones | None = item.actuacion
        contra = (act.contraproducencia or "").strip() or None if act else None
        motivo = (item.motivo_no_realizado or "").strip() or None
        out[iid] = ProcesadosCierreContext(
            motivo_no_realizado=motivo,
            contraproducencia=contra,
            fecha_cierre=item.ejecutado_at,
        )
    return out
