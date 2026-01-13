from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Contribuyente, Domicilio, Rubro


def get_or_create_domicilio(
    data: Optional[Dict[str, Any]],
    contribuyente: Optional[Contribuyente],
    rubro: Optional[Rubro],
) -> Optional[Domicilio]:
    """
    Resuelve (get o create) un `Domicilio` identificándolo por `calle` + `numero`.

    Reglas / comportamiento:
    - Si `data` es `None` o vacío -> devuelve `None`.
    - Si faltan `calle` o `numero` -> devuelve `None` (no intenta crear/buscar).
    - Si viene `calle+numero`:
        - `contribuyente` es obligatorio, si no -> `ValueError`.
        - `rubro` es obligatorio, si no -> `ValueError`.
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

    if contribuyente is None:
        raise ValueError("Si cargás domicilio, debés cargar contribuyente.")
    if rubro is None:
        raise ValueError("Si cargás domicilio, debés cargar rubro.")

    calle = str(calle).strip()
    numero = str(numero).strip()

    dom = Domicilio.query.filter_by(calle=calle, numero=numero).first()
    if dom:
        changed = False
        if dom.contribuyente_id != contribuyente.id:
            dom.contribuyente_id = contribuyente.id
            changed = True
        if dom.rubro_id != rubro.id:
            dom.rubro_id = rubro.id
            changed = True
        if changed:
            db.session.add(dom)
        return dom

    dom = Domicilio(
        calle=calle,
        numero=numero,
        contribuyente_id=contribuyente.id,
        rubro_id=rubro.id,
    )
    db.session.add(dom)
    db.session.flush()
    return dom
