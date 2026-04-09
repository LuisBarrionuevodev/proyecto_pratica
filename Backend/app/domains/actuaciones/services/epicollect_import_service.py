"""
Importación mínima EpiCollect5 → `actuaciones.ec5_uuid` + filas `actuacion_media`.

Matching solo por `actuacion_id` explícito. Medios solo por allowlist de field_ids.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.database import db
from app.domains.actuaciones.config.epicollect_media_fields import (
    EPICOLLECT_MEDIA_FIELDS,
    MEDIA_FIELD_IDS,
)
from app.domains.actuaciones.utils.epicollect_payload import (
    build_payload_non_media_envelope,
    coalesce_epicollect_entry_payload,
    extract_ec5_entry_uuid,
    guess_mime_type_from_url,
    iter_media_urls,
    resolve_field_raw,
)
from app.models import ActuacionEpicollectDetalle, ActuacionMedia, Actuaciones

# Prefijo único para filas generadas por este import (idempotencia por reemplazo).
CATEGORIA_PREFIX = "epicollect."


class EpicollectImportConflictError(ValueError):
    """Conflicto de vinculación de UUID (409)."""


def _get_actuacion_or_404(actuacion_id: int) -> Actuaciones:
    act = Actuaciones.query.get(actuacion_id)
    if not act:
        raise ValueError("Actuación no encontrada.")
    return act


def _validate_ec5_uuid_for_act(act: Actuaciones, entry_uuid: str) -> None:
    """Reglas fuertes de `ec5_uuid` antes de persistir."""
    if act.ec5_uuid and act.ec5_uuid != entry_uuid:
        raise EpicollectImportConflictError(
            "EpiCollect: la actuación ya tiene otro ec5_uuid vinculado; no se puede sobrescribir."
        )

    other = (
        Actuaciones.query.filter(
            Actuaciones.ec5_uuid == entry_uuid,
            Actuaciones.id != act.id,
        ).first()
    )
    if other:
        raise EpicollectImportConflictError(
            "EpiCollect: este ec5_uuid ya está vinculado a otra actuación."
        )


def _delete_epicollect_media_rows(actuacion_id: int) -> None:
    """Quita solo filas creadas por import EpiCollect (prefijo epicollect.)."""
    ActuacionMedia.query.filter(
        ActuacionMedia.actuacion_id == actuacion_id,
        ActuacionMedia.categoria.like(f"{CATEGORIA_PREFIX}%"),
    ).delete(synchronize_session=False)


def _build_media_rows(payload: Dict[str, Any], actuacion_id: int) -> List[ActuacionMedia]:
    """
    Construye filas media según allowlist ordenada.

    Varios field_id pueden compartir la misma categoría semántica; `orden` es
    incremental dentro de cada categoría siguiendo el orden de `EPICOLLECT_MEDIA_FIELDS`.
    """
    rows: List[ActuacionMedia] = []
    orden_por_categoria: Dict[str, int] = {}

    for field_id, categoria_suffix in EPICOLLECT_MEDIA_FIELDS:
        raw = resolve_field_raw(payload, field_id)
        urls = list(iter_media_urls(raw))
        categoria = f"{CATEGORIA_PREFIX}{categoria_suffix}"
        base_orden = orden_por_categoria.get(categoria_suffix, 0)
        for i, url in enumerate(urls):
            mime = guess_mime_type_from_url(url)
            rows.append(
                ActuacionMedia(
                    actuacion_id=actuacion_id,
                    categoria=categoria,
                    url=url[:2048],
                    mime_type=mime,
                    orden=base_orden + i,
                )
            )
        if urls:
            orden_por_categoria[categoria_suffix] = base_orden + len(urls)

    return rows


def _upsert_epicollect_detalle(
    act: Actuaciones,
    payload: Dict[str, Any],
    entry_uuid: str,
) -> None:
    """
    Persiste snapshot no-media (JSON) para la actuación.

    Re-import del mismo entry: sobrescribe ``payload_non_media`` y ``entry_uuid`` en la misma fila.
    """
    envelope = build_payload_non_media_envelope(payload, MEDIA_FIELD_IDS)
    row = ActuacionEpicollectDetalle.query.filter_by(actuacion_id=act.id).first()
    if row is None:
        row = ActuacionEpicollectDetalle(
            actuacion_id=act.id,
            entry_uuid=entry_uuid,
            source="EPICOLLECT",
            payload_non_media=envelope,
        )
    else:
        row.entry_uuid = entry_uuid
        row.source = "EPICOLLECT"
        row.payload_non_media = envelope
    db.session.add(row)


def import_epicollect_entry(actuacion_id: int, payload: Dict[str, Any]) -> Tuple[Actuaciones, int]:
    """
    Vincula un entry EpiCollect a una actuación, sincroniza medios allowlist y guarda detalle no-media.

    Args:
        actuacion_id: actuación destino (único criterio de matching en esta fase).
        payload: JSON crudo del entry (dict).

    Returns:
        Tupla (actuación actualizada, cantidad de filas `actuacion_media` insertadas).

    Raises:
        ValueError: actuación inexistente o payload inválido.
        EpicollectImportConflictError: reglas de `ec5_uuid` (otra actuación o distinto UUID ya guardado).

    Idempotencia:
        Re-import del mismo entry: mismas reglas de UUID; medios `epicollect.*` se reemplazan;
        `actuacion_epicollect_detalle.payload_non_media` se sobrescribe con el nuevo snapshot.
    """
    if not isinstance(payload, dict):
        raise ValueError("EpiCollect: el payload debe ser un objeto JSON.")

    payload = coalesce_epicollect_entry_payload(payload)

    act = _get_actuacion_or_404(actuacion_id)
    entry_uuid = extract_ec5_entry_uuid(payload)
    _validate_ec5_uuid_for_act(act, entry_uuid)

    act.ec5_uuid = entry_uuid

    _delete_epicollect_media_rows(act.id)
    new_rows = _build_media_rows(payload, act.id)
    for r in new_rows:
        db.session.add(r)

    _upsert_epicollect_detalle(act, payload, entry_uuid)

    db.session.add(act)
    db.session.commit()
    db.session.refresh(act)

    return act, len(new_rows)
