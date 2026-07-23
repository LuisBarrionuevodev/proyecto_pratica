from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.domicilios.utils.domicilio_operativo_shared import (
    clonar_domicilio_operativo,
    debe_fork_domicilio_operativo,
)
from app.models import Contribuyente, Domicilio, Rubro


def get_or_create_domicilio(
    data: Optional[Dict[str, Any]],
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
    allow_missing_catalogs: bool = False,
) -> Optional[Domicilio]:
    """
    Resuelve (get o create) un `Domicilio` identificándolo por `calle` + `numero`.

    Reglas / comportamiento:
    - Si `data` es `None` o vacío -> devuelve `None`.
    - Si faltan `calle` o `numero` -> devuelve `None` (no intenta crear/buscar).
    - Si viene `calle+numero`:
        - Por defecto exige `contribuyente` y `rubro`.
        - Si `allow_missing_catalogs=True`, permite crear domicilio sin rubro/contribuyente.
    - Si ya existe un domicilio con esa `calle` y `numero`:
        - Re-asocia `contribuyente_id` y/o `rubro_id` si cambiaron.
        - Hace `db.session.add(dom)` solo si hubo cambios.
        - Devuelve el domicilio existente.
    - Si no existe:
        - Crea un `Domicilio` con `calle`, `numero`, `contribuyente_id`, `rubro_id`.
        - Hace `db.session.add(dom)` y `db.session.flush()` (NO hace commit).
        - Devuelve el domicilio creado.

    Args:
        data: Diccionario con claves esperadas:
            - `calle`: str
            - `numero`: str
        contribuyente: Contribuyente asociado (obligatorio si hay domicilio).
        rubro: Rubro asociado (obligatorio si hay domicilio).

    Returns:
        - `Domicilio` existente o creado, o `None` si no hay datos suficientes para domicilio.

    Raises:
        ValueError: si `data` trae `calle+numero` pero falta `contribuyente` o `rubro`.
    """
    if not data:
        return None

    calle = data.get("calle")
    numero = data.get("numero")

    if not calle or not numero:
        return None

    if not allow_missing_catalogs:
        if contribuyente is None:
            raise ValueError("Si cargás domicilio, debés cargar contribuyente.")
        if rubro is None:
            raise ValueError("Si cargás domicilio, debés cargar rubro.")

    calle = str(calle).strip()
    numero = str(numero).strip()

    raw_nt = data.get("numero_tipo")
    numero_tipo: Optional[str] = None
    if raw_nt is not None and str(raw_nt).strip():
        numero_tipo = str(raw_nt).strip().upper()

    dom = (
        Domicilio.query.filter(
            Domicilio.calle == calle,
            Domicilio.numero == numero,
            Domicilio.deleted_at.is_(None),
        ).first()
    )
    if dom:
        if debe_fork_domicilio_operativo(dom, contribuyente=contribuyente, rubro=rubro):
            dom = clonar_domicilio_operativo(
                dom,
                contribuyente=contribuyente,
                rubro=rubro,
                numero_tipo=numero_tipo,
            )
            db.session.add(dom)
            db.session.flush()
            return dom

        changed = False
        if contribuyente is not None and dom.contribuyente_id is None:
            dom.contribuyente_id = contribuyente.id
            changed = True
        if rubro is not None and dom.rubro_id is None:
            dom.rubro_id = rubro.id
            changed = True
        if numero_tipo is not None and dom.numero_tipo != numero_tipo:
            dom.numero_tipo = numero_tipo
            changed = True
        if changed:
            db.session.add(dom)
        return dom

    dom = Domicilio(
        calle=calle,
        numero=numero,
        numero_tipo=numero_tipo,
        contribuyente_id=contribuyente.id if contribuyente is not None else None,
        rubro_id=rubro.id if rubro is not None else None,
    )
    db.session.add(dom)
    db.session.flush()
    return dom
