from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Contribuyente


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def resolve_contribuyente(data: Optional[Dict[str, Any]]) -> Optional[Contribuyente]:
    """
    Resuelve (modo upsert) un Contribuyente a partir de un payload parcial y lo devuelve.

    Identificación:
    - El contribuyente se identifica por `documento` (campo `doc_nro` en `data`).

    Reglas / comportamiento:
    - Si `data` es `None` o vacío -> devuelve `None`.
    - Si viene `apellido`, `nombre` y/o `razon_social`, entonces `doc_nro` es obligatorio; si falta -> `ValueError`.
    - Si existe un contribuyente con ese documento:
        - Actualiza `apellido` / `nombre` / `razon_social` según claves presentes en `data`.
        - Devuelve la instancia existente (posiblemente actualizada).
    - Si no existe:
        - Crea un nuevo `Contribuyente` con los campos provistos.
        - Hace `flush()` para obtener el `id`.
        - Devuelve la instancia creada.

    Args:
        data: Diccionario con claves opcionales:
            - `doc_nro`: documento (identificador).
            - `apellido`: apellido (opcional).
            - `nombre`: nombre (opcional).
            - `razon_social`: razón social (opcional, persona jurídica).

    Returns:
        - `Contribuyente` existente o creado, o `None` si no hay `data`/`doc_nro`.

    Raises:
        ValueError: si se envían datos de titular sin `doc_nro`.
    """
    if not data:
        return None

    doc = data.get("doc_nro")
    apellido = data.get("apellido")
    nombre = data.get("nombre")
    razon_social = data.get("razon_social")

    # coherencia: si hay datos de titular, doc obligatorio
    if (apellido or nombre or razon_social) and not doc:
        raise ValueError("Documento del contribuyente es obligatorio.")

    if not doc:
        return None

    doc = str(doc).strip()

    c = (
        Contribuyente.query.filter(
            Contribuyente.documento == doc,
            Contribuyente.deleted_at.is_(None),
        ).first()
    )
    if c:
        changed = False
        if apellido is not None and apellido != "" and apellido != c.apellido:
            c.apellido = apellido
            changed = True
        if nombre is not None and nombre != "" and nombre != c.nombre:
            c.nombre = nombre
            changed = True
        if "razon_social" in data:
            new_rs = _clean_str(razon_social)
            if new_rs != c.razon_social:
                c.razon_social = new_rs
                changed = True
        if changed:
            db.session.add(c)
        return c

    c = Contribuyente(
        documento=doc,
        apellido=apellido,
        nombre=nombre,
        razon_social=_clean_str(razon_social),
    )
    db.session.add(c)
    db.session.flush()
    return c
