from __future__ import annotations

from datetime import date

from app.database import db
from app.models import RutaTrabajo


def list_rutas_borrador(
    *,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[RutaTrabajo], int, int]:
    """
    Lista rutas de trabajo en estado BORRADOR (para reabrir en la UI).

    Parámetros:
        fecha_desde: si se informa, incluye solo rutas con fecha >= este día.
        fecha_hasta: si se informa, incluye solo rutas con fecha <= este día.
        page: página 1-based.
        per_page: tamaño de página (acotado internamente).

    Retorno:
        Tupla (filas ordenadas por fecha desc, id desc, total que matchea filtros, per_page efectivo).

    Errores:
        ValueError: page o per_page inválidos.
    """
    if page < 1:
        raise ValueError("page debe ser >= 1")
    per = max(1, min(int(per_page), 100))
    q = db.session.query(RutaTrabajo).filter(RutaTrabajo.estado_ruta == "BORRADOR")
    if fecha_desde is not None:
        q = q.filter(RutaTrabajo.fecha >= fecha_desde)
    if fecha_hasta is not None:
        q = q.filter(RutaTrabajo.fecha <= fecha_hasta)
    total = q.count()
    rows = (
        q.order_by(RutaTrabajo.fecha.desc(), RutaTrabajo.id.desc())
        .offset((page - 1) * per)
        .limit(per)
        .all()
    )
    return rows, int(total), per
