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
        - Actualiza `apellido` / `nombre` / `razon_social` solo si la clave está en `data`
          (incluido `None` o cadena vacía tras normalizar: limpia el campo en BD).
        - Si la clave no está en `data`, el campo existente no se modifica.
        - Devuelve la instancia existente (posiblemente actualizada).
    - Si no existe:
        - Crea un nuevo `Contribuyente` con los campos provistos (solo claves presentes en `data`).
        - Hace `flush()` para obtener el `id`.
        - Devuelve la instancia creada.
    - Tras actualizar un existente con cambios, hace `flush()` para reflejar el estado en la sesión/BD.

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
        if "apellido" in data:
            new_a = _clean_str(apellido)
            if new_a != c.apellido:
                c.apellido = new_a
                changed = True
        if "nombre" in data:
            new_n = _clean_str(nombre)
            if new_n != c.nombre:
                c.nombre = new_n
                changed = True
        if "razon_social" in data:
            new_rs = _clean_str(razon_social)
            if new_rs != c.razon_social:
                c.razon_social = new_rs
                changed = True
        if changed:
            db.session.add(c)
            db.session.flush()
        return c

    kw: Dict[str, Any] = {"documento": doc}
    if "apellido" in data:
        kw["apellido"] = _clean_str(apellido)
    if "nombre" in data:
        kw["nombre"] = _clean_str(nombre)
    if "razon_social" in data:
        kw["razon_social"] = _clean_str(razon_social)
    c = Contribuyente(**kw)
    db.session.add(c)
    db.session.flush()
    return c
