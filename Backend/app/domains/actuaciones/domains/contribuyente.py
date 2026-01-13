from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Contribuyente


def resolve_contribuyente(data: Optional[Dict[str, Any]]) -> Optional[Contribuyente]:
    """
    Resuelve (modo upsert) un Contribuyente a partir de un payload parcial y lo devuelve.

    Identificación:
    - El contribuyente se identifica por `documento` (campo `doc_nro` en `data`).

    Reglas / comportamiento:
    - Si `data` es `None` o vacío -> devuelve `None`.
    - Si viene `apellido` y/o `nombre`, entonces `doc_nro` es obligatorio; si falta -> `ValueError`.
    - Si existe un contribuyente con ese documento:
        - Actualiza `apellido` / `nombre` SOLO si vienen no vacíos y cambiaron.
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

    Returns:
        - `Contribuyente` existente o creado, o `None` si no hay `data`/`doc_nro`.

    Raises:
        ValueError: si se envían datos de persona (apellido/nombre) sin `doc_nro`.
    """
    if not data:
        return None

    doc = data.get("doc_nro")
    apellido = data.get("apellido")
    nombre = data.get("nombre")

    # coherencia: si hay datos de persona, doc obligatorio
    if (apellido or nombre) and not doc:
        raise ValueError("Documento del contribuyente es obligatorio.")

    if not doc:
        return None

    doc = str(doc).strip()

    c = Contribuyente.query.filter_by(documento=doc).first()
    if c:
        changed = False
        if apellido is not None and apellido != "" and apellido != c.apellido:
            c.apellido = apellido
            changed = True
        if nombre is not None and nombre != "" and nombre != c.nombre:
            c.nombre = nombre
            changed = True
        if changed:
            db.session.add(c)
        return c

    c = Contribuyente(
        documento=doc,
        apellido=apellido,
        nombre=nombre,
    )
    db.session.add(c)
    db.session.flush()
    return c
