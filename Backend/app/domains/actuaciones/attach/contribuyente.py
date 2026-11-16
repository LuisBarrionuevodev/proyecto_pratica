from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.domains.actuaciones.attach.documento_identidad_errors import (
    MSG_DOCUMENTO_AMBIGUO,
    DocumentoIdentidadError,
)
from app.domains.establecimientos.services.contribuyente_documento_unico_service import (
    adquirir_lock_para_resolve,
    asegurar_reserva_documento,
    assert_documento_almacenable,
)
from app.domains.establecimientos.services.historial_contribuyente_service import (
    contribuyente_ids_por_documento,
)
from app.models import Contribuyente, ContribuyenteDocumentoUnico


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _aplicar_campos_titular(c: Contribuyente, data: Dict[str, Any]) -> bool:
    """
    Aplica apellido/nombre/razón social con la regla vigente (clave presente pisa, ausente no toca).

    Parámetros:
        c: fila a actualizar.
        data: payload original (presencia de clave importa).

    Retorno:
        True si cambió algún campo.
    """
    changed = False
    if "apellido" in data:
        new_a = _clean_str(data.get("apellido"))
        if new_a != c.apellido:
            c.apellido = new_a
            changed = True
    if "nombre" in data:
        new_n = _clean_str(data.get("nombre"))
        if new_n != c.nombre:
            c.nombre = new_n
            changed = True
    if "razon_social" in data:
        new_rs = _clean_str(data.get("razon_social"))
        if new_rs != c.razon_social:
            c.razon_social = new_rs
            changed = True
    return changed


def resolve_contribuyente(data: Optional[Dict[str, Any]]) -> Optional[Contribuyente]:
    """
    Resuelve (modo upsert) un Contribuyente a partir de un payload parcial y lo devuelve.

    Identificación:
    - El contribuyente se identifica por documento **normalizado** (campo `doc_nro` en `data`):
      se ignoran puntos, guiones y espacios al buscar, y se reutiliza si hay **una**
      coincidencia activa.
    - El valor persistido en altas nuevas es el string ingresado (strip), no el normalizado.

    Reglas / comportamiento:
    - Si `data` es `None` o vacío -> devuelve `None`.
    - Si viene `apellido`, `nombre` y/o `razon_social`, entonces `doc_nro` es obligatorio; si falta -> `ValueError`.
    - Una coincidencia activa: reutiliza esa fila. Actualiza `apellido` / `nombre` / `razon_social`
      solo si la clave está en `data` (incluido `None` o cadena vacía tras normalizar: limpia el campo).
      Si la clave no está en `data`, el campo existente no se modifica.
    - Cero coincidencias: crea un registro bajo GET_LOCK + reserva en `contribuyente_documento_unico`.
      El lock dura hasta commit o rollback de la transacción del llamador.
    - Varias coincidencias activas: no elige, no fusiona, no crea. `DocumentoIdentidadError` DOCUMENTO_AMBIGUO.
    - Documento que no cabe en VARCHAR(11) o queda vacío al normalizar: error 400, sin truncar.

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
        DocumentoIdentidadError: documento inválido, ambiguo o lock ocupado.
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
    norm = assert_documento_almacenable(doc)
    adquirir_lock_para_resolve(norm)

    # PK locking de la reserva: ve la fila commitida por el otro hilo.
    unico = (
        ContribuyenteDocumentoUnico.query.filter_by(documento_normalizado=norm)
        .with_for_update()
        .first()
    )
    if unico is not None:
        c = (
            Contribuyente.query.filter(
                Contribuyente.id == int(unico.contribuyente_id),
                Contribuyente.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )
        if c is not None:
            if _aplicar_campos_titular(c, data):
                db.session.add(c)
                db.session.flush()
            return c

    ids = sorted({int(i) for i in contribuyente_ids_por_documento(doc, for_update=True)})
    if len(ids) > 1:
        raise DocumentoIdentidadError(MSG_DOCUMENTO_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")

    if len(ids) == 1:
        c = (
            Contribuyente.query.filter(
                Contribuyente.id == ids[0],
                Contribuyente.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )
        if c is None:
            raise DocumentoIdentidadError(MSG_DOCUMENTO_AMBIGUO, codigo="DOCUMENTO_AMBIGUO")
        asegurar_reserva_documento(int(c.id), c.documento or doc)
        if _aplicar_campos_titular(c, data):
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
    nested = db.session.begin_nested()
    try:
        asegurar_reserva_documento(int(c.id), doc)
        nested.commit()
    except DocumentoIdentidadError:
        nested.rollback()
        # Otra transacción confirmó primero: no dejar el alta local ni fusionar.
        db.session.delete(c)
        db.session.flush()
        ids_otra = sorted(
            {
                int(i)
                for i in contribuyente_ids_por_documento(doc, for_update=True)
                if int(i) != int(c.id)
            }
        )
        if len(ids_otra) == 1:
            existente = (
                Contribuyente.query.filter(
                    Contribuyente.id == ids_otra[0],
                    Contribuyente.deleted_at.is_(None),
                )
                .with_for_update()
                .first()
            )
            if existente is None:
                raise
            asegurar_reserva_documento(int(existente.id), existente.documento or doc)
            if _aplicar_campos_titular(existente, data):
                db.session.add(existente)
                db.session.flush()
            return existente
        raise
    return c
