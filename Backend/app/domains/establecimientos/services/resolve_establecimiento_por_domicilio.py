from __future__ import annotations

from app.database import db
from app.domains.establecimientos.utils.establecimiento_identidad_logica import (
    eo_canonico_id_para_domicilio,
    identidad_logica_completa,
)
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
        - Si ya existe ficha lógica (mismo contribuyente + domicilio lógico), retorna el id canónico (MIN).
        - Si ya hay ficha 1:1 para ese ``domicilio_id`` sin identidad completa, la reutiliza.
        - Si no, crea fila anclada al domicilio solicitado, ``flush`` y retorna el id.

    Parámetros:
        domicilio_id: FK a ``domicilio`` (ancla física del cierre actual).
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

    if identidad_logica_completa(dom):
        canon_id = eo_canonico_id_para_domicilio(dom)
        if canon_id is not None:
            return int(canon_id)

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
