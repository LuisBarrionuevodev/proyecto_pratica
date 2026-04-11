from __future__ import annotations

from app.database import db
from app.models import Domicilio, EstablecimientoOperativo


def resolve_establecimiento_por_domicilio(
    domicilio_id: int | None,
    *,
    created_by_user_id: int,
) -> int | None:
    """
    Obtiene o crea un ``EstablecimientoOperativo`` para el domicilio dado.

    Qué hace:
        - Si ``domicilio_id`` es None, no hace nada (retorna None).
        - Si el domicilio no existe o está soft-deleted, retorna None (no enlaza).
        - Si ya hay ficha para ese domicilio, retorna su id.
        - Si no, crea fila, ``flush`` en sesión actual (sin commit) y retorna el id.

    Parámetros:
        domicilio_id: FK a ``domicilio`` (ancla del establecimiento).
        created_by_user_id: usuario que dispara la creación (auditoría).

    Retorno:
        id de ``establecimiento_operativo``, o None si no aplica.

    Errores:
        Ninguno explícito; fallos de integridad suben al llamador al hacer commit.
    """
    if domicilio_id is None:
        return None

    dom = db.session.get(Domicilio, domicilio_id)
    if dom is None:
        return None
    if getattr(dom, "deleted_at", None) is not None:
        return None

    existing = EstablecimientoOperativo.query.filter_by(domicilio_id=domicilio_id).first()
    if existing is not None:
        return int(existing.id)

    row = EstablecimientoOperativo(
        domicilio_id=domicilio_id,
        created_by_user_id=created_by_user_id,
    )
    db.session.add(row)
    db.session.flush()
    return int(row.id)
